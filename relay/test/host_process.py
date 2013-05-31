#!/usr/bin/python
import sys

from sys import stdout
from argparse import ArgumentParser
from struct import unpack
from threading import Lock
from google.protobuf.message import DecodeError

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol, \
    ReconnectingClientFactory
from twisted.python.log import startLogging
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.python import log

from message_types.command_pb2 import Command
from message_types.hello_pb2 import Hello, HostProcessHelloResponse
from message_types import build_msg_data_hphello
from base_protocol import BaseProtocol
from read_buffer import ReadBuffer


class RealServer(object):
    """This receives the actual proxied data."""
    
    def __init__(self, connection):
        self.__connection = connection
        
    def receive_data(self, proxied_data):
        log.msg("Real server received (%d) bytes." % (len(proxied_data)))


class HostProcess(BaseProtocol):
    """This is a connection to the relay server. It knows how to configure 
    itself, and then forward all subsequent data to the "RealServer" instance.
    """
    
    __locker = Lock()
    
    def __init__(self):
        self.__configured = False
        self.__buffer = ""

        self.__session_id = None;
        self.__relay_host = None;
        self.__relay_port = None;

        self.__real_server = RealServer(self)
    
    def connectionMade(self):
        log.msg("We've successfully connected to the relay server. "
                      "Sending hello.")
                
        hello = build_msg_data_hphello()
        self.write_message(hello)

    def __get_message(self):
        """We expect exactly one message within the entire session. Return None 
        if not found.
        """

        with self.__class__.__locker:
            length_length = 4
            current_bytes = len(self.__buffer)
            if current_bytes < length_length:
                return None
    
            length_bytes = self.__buffer[0:length_length]
            (length,) = unpack('>I', length_bytes)
    
            if current_bytes < (length_length + length):
                return None
                
            message = self.__buffer[length_length:(length_length + length)]
            self.__buffer = self.__buffer[(length_length + length):]

        return message

    def __handle_configuration_data(self, data):
        """Our connection has not been configured yet."""

        with self.__class__.__locker:
            self.__buffer += data

        message_raw = self.__get_message()
        if message_raw is None:
            return

        response = self.parse_or_raise(message_raw, HostProcessHelloResponse)

        self.__session_id = response.session_id;
        self.__relay_host = response.relay_host;
        self.__relay_port = int(response.relay_port);

        log.msg("Received hello response: SESSION-ID=(%d) RHOST=[%s] "
                      "RPORT=(%d)" % 
                      (self.__session_id, self.__relay_host, 
                       self.__relay_port))

        self.__configured = True
    
    def dataReceived(self, data):
        try:
            if self.__configured is False:
                self.__handle_configuration_data(data)
            else:
                with self.__class__.__locker:
                    if self.__buffer:
                        data = self.__buffer + data
                        self.__buffer = ""
                    
                self.__real_server.receive_data(data)
        except Exception as e:
            log.err()


class CommandListener(BaseProtocol):
    """The relay server will emit messages to us over a separate command 
    channel. The messages are referred to as commands, but are also referred-to 
    as "announcements".
    """    
    
    def __init__(self):
        self.__buffer = ReadBuffer()
    
    def connectionMade(self):
        pass

    def __handle_new_connection(self, properties):
        """We're about to receive data from a new client."""
        
        self.__assigned_session_id = properties.assigned_to_session 
        
        log.msg("Received announcement of assignment to session-ID "
                      "(%d)." % (self.__assigned_session_id))
        
    def __handle_dropped_connection(self, properties):
        """The client assigned to us has dropped their connection. Ours will be
        dropped imminently."""
        
        session_id = properties.session_id

        log.msg("Received announcement of a connection drop for client "
                      "with session-ID (%d)." % (session_id))

    def __handle_announcement(self, announcement):
        log.msg("Receiving an announcement with message-type of (%d)." % 
                      (announcement.message_type))
        
        if announcement.message_type == Command.CONNECTION_OPEN:
            self.__handle_new_connection(announcement.open_properties)
        elif announcement.message_type == Command.CONNECTION_CLOSE:
            self.__handle_dropped_connection(announcement.drop_properties)

    def dataReceived(self, data):
        try:
            self.__buffer.push(data)

            message_raw = self.__buffer.read_message()
            if message_raw is None:
                return

            announcement = self.parse_or_raise(message_raw, Command)
            self.__handle_announcement(announcement)            
        except:
            log.err()


class HostProcessClientFactory(ClientFactory):
    """This class manages instance-creation for the outgoing host-process 
    connections. It will reconnect if a connection is broken or times-out while 
    trying to connect.
    """

    def __repr__(self):
        return 'HostProcessClientFactory'
    
    def startedConnecting(self, connector):
        log.msg("Started to connect.")

    def buildProtocol(self, addr):
        log.msg("Connected.")
        return HostProcess()


class CommandListenerClientFactory(ReconnectingClientFactory):
    """This class manages instance-creation for the outgoing command
    connections. It will reconnect if a connection is broken or times-out while 
    trying to connect.
    """

    def __repr__(self):
        return 'CommandListenerClientFactory'

    def startedConnecting(self, connector):
        log.msg("Started to connect.")

    def buildProtocol(self, addr):
        log.msg("Connected.")
        return CommandListener()

def main():
    parser = ArgumentParser(description='Start a protocol-agnostic relay '
                                        'server.')

    parser.add_argument('host', nargs='?', default='localhost')
    
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

    host = args.host
    dport = args.dport
    cport = args.cport

    startLogging(sys.stdout)

    reactor.connectTCP(host, dport, HostProcessClientFactory())
    reactor.connectTCP(host, cport, CommandListenerClientFactory())
    reactor.run()

if __name__ == '__main__':
    main()

