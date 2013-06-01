
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import sys

from argparse import ArgumentParser
from threading import Lock
from collections import OrderedDict
from twisted.internet import reactor, protocol
from twisted.python.log import startLogging
from twisted.python import log

from relayserver.read_buffer import ReadBuffer
from relayserver.message_types.hello_pb2 import Hello
from relayserver.message_types import build_msg_cmd_connopen,\
                                      build_msg_cmd_conndrop,\
                                      build_msg_data_hphelloresponse

from relayserver.base_protocol import BaseProtocol

ports = None

# TODO: As Twisted mostly runs synchronously, see if there's someway we can 
#       spin-off write requests so that control can return to the reactor. 


class _AssignmentManager(object):
    # Lists of current connections.
    __client_list = OrderedDict()
    __hp_assigned_list = OrderedDict()
    __hp_waiting_list = OrderedDict()

    # Forward and reverse maps expressing assignments.
    __map_client_to_hp = {}
    __map_hp_to_client = {}

    __locker = Lock()

    def queue_new_hp(self, hp_connection):
        cls = self.__class__

        with cls.__locker:
            cls.__hp_waiting_list[hp_connection.session_id] = hp_connection

    def get_assigned_hp(self, client_session_id):
        cls = self.__class__
        
        with cls.__locker:
            return cls.__map_client_to_hp[client_session_id] \
                    if client_session_id \
                    in cls.__map_client_to_hp \
                    else None

    def get_client_for_hp(self, hp_session_id):
        cls = self.__class__
        
        with cls.__locker:
            return cls.__map_hp_to_client[hp_session_id] \
                    if hp_session_id \
                    in cls.__map_hp_to_client \
                    else None

    def assign_new_client(self, client_connection):
        cls = self.__class__
        
        with cls.__locker:
            # Make sure the host-process is listening on the command-channel.
            if CommandServer.get_command_channel() is None:
                log.msg("We're denying new client with session-ID (%d) "
                        "because a host-process command-channel is not "
                        "connected (assuming no HP available)." % 
                        (client_connection.session_id))
                
                return False
    
            # Make sure there is at least one host-process connection waiting
            # to service a request.

            if not cls.__hp_waiting_list:
                log.msg("We're denying new client with session-ID (%d) "
                        "because there are no available host-processes." % 
                        (client_connection.session_id))
                
                return False

            # Dequeue an unassigned HP connection.
            for available_hp_connection in cls.__hp_waiting_list.itervalues():
                hp_connection = available_hp_connection
                break
            
            del cls.__hp_waiting_list[hp_connection.session_id]

            # Assign the HP connection.
            cls.__map_client_to_hp[client_connection.session_id] = \
                hp_connection
            cls.__map_hp_to_client[hp_connection.session_id] = \
                client_connection

            # Store the assigned HP connection.
            cls.__hp_assigned_list[hp_connection.session_id] = \
                hp_connection

            # Store the client connection.
            cls.__client_list[client_connection.session_id] = self

            log.msg("Client with session-ID (%d) has been assigned to host-"
                    "process with session-ID (%d)." % 
                    (client_connection.session_id, hp_connection.session_id))

        # Now, announce the assignment on the command-channel, and respond 
        # to the client. Note that, although we don't guarantee the order,
        # the client would first have to receive the message and -then-
        # send data, whereas the host process may just have to perform a
        # couple of trivial operations, if any, to prepare a session that
        # should already be ready to go.

        # Emit an assignment message on the command-channel.
        CommandServer.get_command_channel().announce_assignment(hp_connection)

        return True

    def connection_lost_from_client(self, session_id):
        cls = self.__class__
        
        with cls.__locker:
            if session_id in cls.__map_client_to_hp:
                # A client connection dropped. This connection will only exist 
                # under assignment.
    
                mapped_hp = cls.__map_client_to_hp[session_id]
                
                log.msg("Client with session-ID (%d) mapped to host-process "
                        "with session-ID (%d) has dropped." % 
                        (session_id, mapped_hp.session_id))
    
                del cls.__map_client_to_hp[session_id]
                del cls.__map_hp_to_client[mapped_hp.session_id]
                del cls.__client_list[session_id]
                del cls.__hp_assigned_list[mapped_hp.session_id]
    
                command_channel = CommandServer.get_command_channel()
                if command_channel is not None:
                    command_channel.announce_drop(mapped_hp)
    
                reactor.callLater(5, mapped_hp.transport.loseConnection)

    def connection_lost_from_hp(self, session_id):
        cls = self.__class__
        
        with cls.__locker:
            if session_id in cls.__hp_waiting_list:
                log.msg("Unassigned host-process with session-ID (%d) has "
                        "dropped." % (session_id))
    
                del cls.__hp_waiting_list[session_id]
                
            elif session_id in cls.__map_hp_to_client:
                # An HP connection dropped. We've stated elsewhere that if this
                # is currently assigned, the result is undefined. We do our 
                # honest and simplest best, here, though.
    
                mapped_client = cls.__map_hp_to_client[session_id]
    
                log.msg("Host-process with session-ID (%d) mapped to client "
                        "with session-ID (%d) has dropped." % 
                        (session_id, mapped_client.session_id))
    
                del cls.__map_client_to_hp[mapped_client.session_id]
                del cls.__map_hp_to_client[session_id]
                del cls.__client_list[mapped_client.session_id]
                del cls.__hp_assigned_list[session_id]
    
                mapped_client.transport.loseConnection()

_assignments = _AssignmentManager()


class TrivialClientServer(BaseProtocol):
    """Handles operations for the client data channel."""

    def connectionMade(self):
        log.msg("Client with session-ID (%d) has connected." % 
                (self.session_id))

        try:
            if _assignments.assign_new_client(self) is False:
                self.transport.loseConnection()
        except:
            log.err()

    def dataReceived(self, data):
        try:
            hp_connection = _assignments.get_assigned_hp(self.session_id)
            hp_connection.transport.write(data)
        except:
            log.err()

    def connectionLost(self, reason):
        try:
            _assignments.connection_lost_from_client(self.session_id)
        except:
            log.err()

    @property
    def session_id(self):
        return self.transport.sessionno
    

class HostProcessServer(BaseProtocol):
    """Handles operations for the host-process data channel."""

    def __init__(self):
        self.__buffer = ReadBuffer()

    def dataReceived(self, data):
        cls = self.__class__

        try:
            client = _assignments.get_client_for_hp(self.session_id)
            if client is not None:
                client.transport.write(data)
                return
        
            self.__buffer.push(data)
    
            message_raw = self.__buffer.read_message()
            if message_raw is None:
                return
    
            hello = self.parse_or_raise(message_raw, Hello)
            self.__handle_hostprocess_hello()
        except:
            log.err()

    def connectionMade(self):
        log.msg("A data connection has been established with connection "
                "having session-ID (%d), but it will need to say hello." % 
                (self.session_id))

    def connectionLost(self, reason):
        try:
            _assignments.connection_lost_from_hp(self.session_id)
        except:
            log.err()
        
    def __handle_hostprocess_hello(self):
        """Handle a host-process hello."""

        cls = self.__class__

        try:
            log.msg("Host-process with session-ID (%d) has said hello." % 
                    (self.session_id))
    
            _assignments.queue_new_hp(self)
    
            host_info = self.transport.getHost()
            response = build_msg_data_hphelloresponse(self.session_id, 
                                                      host_info.host, 
                                                      ports[2])
    
            self.write_message(response)
        except:
            log.err()

    @property
    def session_id(self):
        return self.transport.sessionno
    

class CommandServer(BaseProtocol):
    """Handles operations for host-process command-channel."""

    __command_channel = None

    def __init__(self):
        self.__buffer = ReadBuffer()

    def dataReceived(self, data):
        self.__buffer.push(data)

        message_raw = self.__buffer.read_message()
        if message_raw is None:
            return

        # We don't actually expect any data to be sent to us. Do not take any 
        # further action, here.

    def connectionLost(self, reason):
        log.msg("Command channel dropped.")
        self.__class__.__command_channel = None
        
    def connectionMade(self):
        log.msg("Command channel connected.")
        self.__class__.__command_channel = self
        
    @classmethod
    def get_command_channel(cls):
        return cls.__command_channel

    def announce_assignment(self, hp_connection):
        log.msg("Announcing assignment of new client to HP session "
                      "(%d)." % (hp_connection.session_id))
        
        command = build_msg_cmd_connopen(hp_connection.session_id)
        self.write_message(command)
                
    def announce_drop(self, hp_connection):
        log.msg("Announcing drop of client assigned to HP session "
                      "(%d)." % (hp_connection.session_id))

        command = build_msg_cmd_conndrop(hp_connection.session_id)
        self.write_message(command)


class _GeneralFactory(protocol.ServerFactory):
    def __init__(self, description):
        """ServerFactory doesn't have a constructor and it's not a new-style 
        class, so we can't call it."""
        
        self.__description = description

    def __repr__(self):
        return ("GeneralFactory(%s)" % (self.__description))

def main():
    global ports

    parser = ArgumentParser(description='Start a protocol-agnostic relay '
                                        'server.')

    parser.add_argument('dport', 
                        nargs='?', 
                        default=8000, 
                        type=int, 
                        help="Port for host-process data-channel connections.")

    parser.add_argument('cport', 
                        nargs='?', 
                        default=8001, 
                        type=int, 
                        help="Port for host-process command-channel "
                             "connections.")

    parser.add_argument('tport', 
                        nargs='?', 
                        default=8002, 
                        type=int, 
                        help="Port for client data-channel connections.")

    args = parser.parse_args()
    ports = (args.dport, args.cport, args.tport)

    #startLogging(sys.stdout)

    relayFactory = _GeneralFactory("HostProcessServer")
    relayFactory.protocol = HostProcessServer
    relayFactory.connections = {}

    commandFactory = _GeneralFactory("CommandServer")
    commandFactory.protocol = CommandServer
    commandFactory.connections = {}

    trivialFactory = _GeneralFactory("TrivialClientServer")
    trivialFactory.protocol = TrivialClientServer
    trivialFactory.connections = {}

    reactor.listenTCP(ports[0], relayFactory)
    reactor.listenTCP(ports[1], commandFactory)
    reactor.listenTCP(ports[2], trivialFactory)
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()

