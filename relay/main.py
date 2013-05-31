
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import sys

from argparse import ArgumentParser
from threading import Lock
from collections import OrderedDict
from twisted.internet import reactor, protocol
from twisted.python.log import startLogging
from twisted.python import log

from relay.read_buffer import ReadBuffer
from relay.message_types.hello_pb2 import Hello
from relay.message_types import build_msg_cmd_connopen, build_msg_cmd_conndrop,\
                                build_msg_data_hphelloresponse,\
                                build_msg_data_chelloresponse
from relay.base_protocol import BaseProtocol


class RelayServer(BaseProtocol):
    """Handles operations for client/host-process data channel."""

    # Lists of current connections.
    __client_list = OrderedDict()
    __hp_assigned_list = OrderedDict()
    __hp_waiting_list = OrderedDict()

    # Forward and reverse maps expressing assignments.
    __map_client_to_hp = {}
    __map_hp_to_client = {}

    __locker = Lock()

    def __init__(self):
        self.__buffer = ReadBuffer()

    def __can_proxy(self, data):
        """If we're under assignment, figure out which host to forward the data 
        to, and do it.
        """
    
        cls = self.__class__

        to = None

        with cls.__locker:
            if self.session_no in cls.__map_client_to_hp:
                to = cls.__map_client_to_hp[self.session_no]
            elif self.session_no in cls.__map_hp_to_client:
                to = cls.__map_hp_to_client[self.session_no]

        if to is not None:
            to.transport.write(data)
            return True
        else:
            return False

    def dataReceived(self, data):
        cls = self.__class__

        try:
            # If an assignment exists, just transfer data.
            if self.__can_proxy(data):
                return
        
            self.__buffer.push(data)
    
            message_raw = self.__buffer.read_message()
            if message_raw is None:
                return
    
            hello = self.parse_or_raise(message_raw, Hello)
            self.__handle_hello(hello)
        except:
            log.err()

    def connectionMade(self):
        log.msg("A data connection has been established with connection "
                "having session-ID (%d), but it will need to say hello." % 
                (self.session_no))

        self.__class__.__command_channel = self

    def connectionLost(self, reason):
        cls = self.__class__

        try:
            if self.session_no in cls.__hp_waiting_list:
                log.msg("Unassigned host-process with session-ID (%d) has "
                        "dropped." % (self.session_no))

                del cls.__hp_waiting_list[self.session_no]
            elif self.session_no in cls.__map_client_to_hp:
                # A client connection dropped. This connection will only exist 
                # under assignment.

                mapped_hp = cls.__map_client_to_hp[self.session_no]
                
                log.msg("Client with session-ID (%d) mapped to host-process "
                        "with session-ID (%d) has dropped." % 
                        (self.session_no, mapped_hp.session_no))

                del cls.__map_client_to_hp[self.session_no]
                del cls.__map_hp_to_client[mapped_hp.session_no]
                del cls.__client_list[self.session_no]
                del cls.__hp_assigned_list[mapped_hp.session_no]

                command_channel = CommandServer.get_command_channel()
                if command_channel is not None:
                    command_channel.announce_drop(mapped_hp.session_no)

# TODO: Wait a few seconds, and -then- drop the connection.
                mapped_hp.transport.loseConnection()
            elif self.session_no in cls.__map_hp_to_client:
                # An HP connection dropped. We've stated elsewhere that if this
                # is currently assigned, the result is undefined. We do our 
                # honest and simplest best, here, though.

                mapped_client = cls.__map_hp_to_client[self]

                log.msg("Host-process with session-ID (%d) mapped to client "
                        "with session-ID (%d) has dropped." % 
                        (self.session_no, mapped_client.session_no))

                del cls.__map_client_to_hp[mapped_client.session_no]
                del cls.__map_hp_to_client[self.session_no]
                del cls.__client_list[mapped_client.session_no]
                del cls.__hp_assigned_list[self.session_no]

                mapped_client.transport.loseConnection()
        except:
            log.err()
        
    def __handle_client_hello(self, client_hello_properties):
        """Handle a client hello. There aren't any defined properties in the 
        initial client message, yet, so the properties presented are ignorable.
        """

        cls = self.__class__

        log.msg("Client with session-ID (%d) has said hello." % 
                (self.session_no))

        try:
            # Make sure the host-process is listening on the command-channel.
            if CommandServer.get_command_channel() is None:
                log.msg("We're denying new client with session-ID (%d) "
                        "because a host-process command-channel is not "
                        "connected (assuming no HP available)." % 
                        (self.session_no))
                
                response = build_msg_data_chelloresponse(False)
                self.write_message(response)
# TODO: Wait for a few seconds and drop the connection.
                return

            # Make sure there is at least one host-process connection waiting
            # to service a request.
            with cls.__locker:
                if not cls.__hp_waiting_list:
                    log.msg("We're denying new client with session-ID (%d) "
                            "because there are no available host-processes." % 
                            (self.session_no))
                    
                    response = build_msg_data_chelloresponse(False)
                    self.write_message(response)
# TODO: Wait for a few seconds and drop the connection.
                    return

                # Dequeue an unassigned HP connection.
                hp_connection = cls.__hp_waiting_list.iter_values()[0]
                del cls.__hp_waiting_list[hp_connection.session_no]

                # Assign the HP connection.
                cls.__map_client_to_hp[self.session_no] = hp_connection
                cls.__map_hp_to_client[hp_connection.session_no] = self

                # Store the assigned HP connection.
                cls.__hp_assigned_list[hp_connection.session_no] = \
                    hp_connection

                # Store the client connection.
                cls.__client_list[self.session_no] = self

                log.msg("Client with session-ID has been assigned to host-"
                        "process with session-ID (%d)." % 
                        (self.session_no, hp_connection.session_no))

# TODO: Implement deferred so that we can guarantee the response sequence, 
#       here.
            # Emit an assignment message on the command-channel.
            CommandServer.get_command_channel().\
                          announce_assignment(self.session_no)

            # Respond to the client.
            response = build_msg_data_chelloresponse(True)
            self.write_message(response)

        except:
            log.err()

    def __handle_hostprocess_hello(self, hostprocess_hello_properties):
        """Handle a host-process hello. There aren't any defined properties in 
        the initial host-process message, yet, so the properties presented are 
        ignorable.
        """

        cls = self.__class__

        log.msg("Host-process with session-ID (%d) has said hello." % 
                (self.session_no))

        with cls.__locker:
            cls.__hp_waiting_list[self.session_no] = self

            host_info = self.transport.getHost()
            response = build_msg_data_hphelloresponse(self.session_no, 
                                                      host_info.host, 
                                                      host_info.port)

            self.write_message(response)
                                    
    def __handle_hello(self, hello):
        if hello.peer_type == Hello.CLIENT:
            properties = hello.client_properties
            self.__handle_client_hello(properties)
            
        elif hello.peer_type == Hello.HOST_PROCESS:
            properties = hello.hostprocess_properties
            self.__handle_hostprocess_hello(properties)

    @property
    def session_no(self):
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

    def announce_assignment(self, hp_session_id):
        log.msg("Announcing assignment of new client to HP session "
                      "(%d)." % (hp_session_id))
        
        command = build_msg_cmd_connopen(hp_session_id)
        self.write_message(command)
                
    def announce_drop(self, hp_session_id):
        log.msg("Announcing drop of client assigned to HP session "
                      "(%d)." % (hp_session_id))

        command = build_msg_cmd_conndrop(hp_session_id)
        self.write_message(command)


class _GeneralFactory(protocol.ServerFactory):
    def __init__(self, description):
        """ServerFactory doesn't have a constructor and it's not a new-style 
        class, so we can't call it."""
        
        self.__description = description

    def __repr__(self):
        return ("GeneralFactory(%s)" % (self.__description))

def main():
    parser = ArgumentParser(description='Start a protocol-agnostic relay '
                                        'server.')

    parser.add_argument('dport', 
                        nargs='?', 
                        default=8000, 
                        type=int, 
                        help="Port for client and host-process data-channel "
                             "connections.")

    parser.add_argument('cport', 
                        nargs='?', 
                        default=8001, 
                        type=int, 
                        help="Port for host-process command-channel "
                             "connections.")

    args = parser.parse_args()

    dport = args.dport
    cport = args.cport

    startLogging(sys.stdout)

    relayFactory = _GeneralFactory("RelayServer")
    relayFactory.protocol = RelayServer
    relayFactory.connections = {}

    commandFactory = _GeneralFactory("CommandServer")
    commandFactory.protocol = CommandServer
    commandFactory.connections = {}

    reactor.listenTCP(dport, relayFactory)
    reactor.listenTCP(cport, commandFactory)
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()

