#!/usr/bin/python

from argparse import ArgumentParser
from sys import stdout

from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory, ClientFactory
from twisted.python.log import startLogging
from twisted.python import log

from relay.message_types.hello_pb2 import ClientHelloResponse
from relay.message_types import build_msg_data_chello
from relay.endpoint import EndpointBaseProtocol

# TODO: Make sure the data going into RealClient goes in serially (so that we 
#       can guarantee ordering). 


class RealClient(object):
    """This receives the actual proxied data."""
    
    def __init__(self, connection):
        self.__connection = connection
        
    def receive_data(self, proxied_data):
        log.msg("Real client received (%d) bytes." % (len(proxied_data)))

    def ready(self):
        log.msg("Real client has been sent the ready signal.")


class Client(EndpointBaseProtocol):
    """This is a connection to the relay server. It knows how to configure 
    itself, and then forward all subsequent data to the "RealServer" instance.
    """
    
    def __init__(self):
        EndpointBaseProtocol.__init__(self)
        
        self.__configured = False
        self.__buffer_cleared = False
        self.__real_client = RealClient(self)
    
    def connectionMade(self):
        log.msg("We've successfully connected to the relay server. "
                      "Sending hello.")
                
        hello = build_msg_data_chello()
        self.write_message(hello)

    def connectionLost(self, reason):
        log.msg("We have been disconnected from the relay-server. The host"
                "process must've gone away.")

    def __handle_configuration_data(self, data):
        """Our connection has not been configured yet."""

        self.push_data(data)

        message_raw = self.get_initial_message()
        if message_raw is None:
            return

        response = self.parse_or_raise(message_raw, ClientHelloResponse)

        # A host-process wasn't available to service us.
        if response.assigned is False:
            log.msg("A host-process isn't available to service us.")
            self.transport.loseConnection()
            return

        log.msg("We have connected and have been assigned to a host-process. "
                "Ready to proceed with regular data.")

        self.__configured = True
    
        self.__real_client.ready()
    
    def dataReceived(self, data):
        try:
            if self.__configured is False:
                self.__handle_configuration_data(data)
            else:
                if self.__buffer_cleared is False:
                    data = self.get_and_clear_buffer() + data
                    self.__buffer_cleared = True
                    
                self.__real_client.receive_data(data)
        except Exception as e:
            log.err()


class ClientClientFactory(ReconnectingClientFactory):
    """This class manages instance-creation for the outgoing client connection. 
    It will reconnect if a connection is broken or times-out while 
    trying to connect.
    """

    def __repr__(self):
        return 'ClientClientFactory'
    
    def startedConnecting(self, connector):
        log.msg("Started to connect.")

    def buildProtocol(self, addr):
        log.msg("Connected client.")
        return Client()


def main():
    parser = ArgumentParser(description="Connect a client application to a "
                                        "host-process by way of the relay " 
                                        "server.")

    parser.add_argument('host', 
                        nargs='?', 
                        default='localhost', 
                        help="The hostname/IP of the relay-server.")
    
    parser.add_argument('dport', 
                        nargs='?', 
                        default=8000, 
                        type=int, 
                        help="Port for client and host-process data-channel "
                             "connections.")

    args = parser.parse_args()

    host = args.host
    dport = args.dport

    startLogging(stdout)

    reactor.connectTCP(host, dport, ClientClientFactory())
    reactor.run()

if __name__ == '__main__':
    main()

