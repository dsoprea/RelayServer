#!/usr/bin/python

from argparse import ArgumentParser
from sys import stdout

from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory, ClientFactory
from twisted.python.log import startLogging
from twisted.python import log

from relay.message_types.hello_pb2 import HostProcessHelloResponse
from relay.message_types import build_msg_data_hphello
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
        self.__real_server = RealClient(self)
    
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
                data = self.get_and_clear_buffer() + data
                self.__real_server.receive_data(data)
        except Exception as e:
            log.err()


class ClientClientFactory(ClientFactory):
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
    parser = ArgumentParser(description='Start a protocol-agnostic relay '
                                        'server.')

    parser.add_argument('host', nargs='?', default='localhost')
    
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

