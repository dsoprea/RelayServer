#!/usr/bin/python

from argparse import ArgumentParser
from sys import stdout

from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.python.log import startLogging
from twisted.python import log

from relayserver.message_types.command_pb2 import Command
from relayserver.message_types.hello_pb2 import HostProcessHelloResponse
from relayserver.message_types import build_msg_data_hphello
from relayserver.base_protocol import BaseProtocol
from relayserver.endpoint import EndpointBaseProtocol
from relayserver.read_buffer import ReadBuffer

from relayserver.config import EndpointServer


class HostProcess(EndpointBaseProtocol):
    """This is a connection to the relay server. It knows how to configure 
    itself, and then forward all subsequent data to the "RealServer" instance.
    """
    
    def __init__(self, factory):
        EndpointBaseProtocol.__init__(self)

        self.__factory = factory
        self.__configured = False

        self.__session_id = None;
        self.__relay_host = None;
        self.__relay_port = None;

        self.__buffer_cleared = False
        self.__real_server = EndpointServer(self)
    
    def connectionLost(self, reason):
        log.msg("Host-process with session-no (%d) has had its connection "
                "dropped." % (self.__session_id))

        self.__real_server.shutdown()
    
    def connectionMade(self):
        log.msg("We've successfully connected to the relay server. "
                      "Sending hello.")
                
        hello = build_msg_data_hphello()
        self.write_message(hello)

    def __handle_configuration_data(self, data):
        """Our connection has not been configured yet."""

        self.push_data(data)

        message_raw = self.get_initial_message()
        if message_raw is None:
            return

        response = self.parse_or_raise(message_raw, HostProcessHelloResponse)

        self.__session_id = response.session_id;
        self.__relay_host = response.relay_host;
        self.__relay_port = int(response.relay_port);

        log.msg("Received hello response: SESSION-NO=(%d) RHOST=[%s] "
                      "RPORT=(%d)" % 
                      (self.__session_id, self.__relay_host, 
                       self.__relay_port))

        self.__configured = True
        self.__factory.resetDelay()
    
    def dataReceived(self, data):
        try:
            if self.__configured is False:
                self.__handle_configuration_data(data)
            else:
                if self.__buffer_cleared is False:
                    data = self.get_and_clear_buffer() + data
                    self.__buffer_cleared = True

                self.__real_server.receive_data(data)
        except Exception as e:
            log.err()

    @property
    def session_id(self):
        return self.__session_id

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
        
        assigned_session_id = properties.assigned_to_session 
        
        log.msg("Received announcement of assignment to session-no "
                      "(%d)." % (assigned_session_id))
        
    def __handle_dropped_connection(self, properties):
        """The client assigned to us has dropped their connection. Ours will be
        dropped imminently."""
        
        session_id = properties.session_id

        log.msg("Received announcement of a connection drop for client "
                      "with session-no (%d)." % (session_id))

    def __handle_announcement(self, announcement):
        log.msg("Receiving an announcement with message-type of (%d)." % 
                      (announcement.message_type))
        
        if announcement.message_type == Command.CONNECTION_OPEN:
            self.__handle_new_connection(announcement.open_properties)
        elif announcement.message_type == Command.CONNECTION_DROP:
            self.__handle_dropped_connection(announcement.drop_properties)

    def dataReceived(self, data):
        log.msg("(%d) bytes of data received on command-channel." % (len(data)))
        
        try:
            self.__buffer.push(data)

            message_raw = self.__buffer.read_message()
            if message_raw is None:
                return

            log.msg("Message extracted from command-channel.")

            announcement = self.parse_or_raise(message_raw, Command)
            self.__handle_announcement(announcement)            
        except:
            log.err()


class HostProcessClientFactory(ReconnectingClientFactory):
    """This class manages instance-creation for the outgoing host-process 
    connections. It will reconnect if a connection is broken or times-out while 
    trying to connect.
    """

    def __repr__(self):
        return 'HostProcessClientFactory'
    
    def startedConnecting(self, connector):
        log.msg("Started to connect.")

    def buildProtocol(self, addr):
        log.msg("Connected host-process.")
        return HostProcess(self)


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
        log.msg("Connected command-listener.")
        
        # We don't have any obligatory communication that happens at the top of
        # a command connection. Just mark it as successful, immediately.
        self.resetDelay()

        return CommandListener()

def main():
    parser = ArgumentParser(description="Start the host process and establish "
                                        "N connections to the relay server.")

    parser.add_argument('host', 
                        nargs='?', 
                        default='localhost', 
                        help="The hostname/IP of the relay-server.")
    
    parser.add_argument('-n', '--num-connections', 
                        nargs='?', 
                        default=10, 
                        type=int, 
                        help="Number of connections to maintain.")

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

    args = parser.parse_args()

    host = args.host
    num_connections = args.num_connections
    dport = args.dport
    cport = args.cport

    #startLogging(stdout)

    reactor.connectTCP(host, cport, CommandListenerClientFactory())

    # Spawn a series of connections to wait for incoming requests. As these are
    # "reconnecting" factories, they will all try to reconnect when their
    # connections are dropped after each client has finished-up (or for any 
    # other reason).
    i = num_connections
    while i > 0:
        reactor.connectTCP(host, dport, HostProcessClientFactory())
        i -= 1

    reactor.run()

if __name__ == '__main__':
    main()

