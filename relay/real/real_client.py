from twisted.python import log

from relay.real.ireal_client import IRealClient


class RealClient(IRealClient):
    """This receives the actual proxied data."""
    
    def __init__(self, connection):
        self.__connection = connection
        
    def receive_data(self, proxied_data):
        log.msg("Real client received (%d) bytes: %s" % 
                (len(proxied_data), proxied_data))

    def ready(self):
        log.msg("Real client has been sent the ready signal.")
        
        self.__connection.transport.write("Test from client.")

    def shutdown(self):
        pass
