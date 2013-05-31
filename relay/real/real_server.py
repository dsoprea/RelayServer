from twisted.python import log

from relay.real.ireal_server import IRealServer


class RealServer(IRealServer):
    """This receives the actual proxied data."""
    
    def __init__(self, connection):
        self.__connection = connection
        
    def receive_data(self, proxied_data):
        log.msg("Real server received (%d) bytes: %s" % 
                (len(proxied_data), proxied_data))

        log.msg("Echoing.")
        self.__connection.transport.write(proxied_data)

    def shutdown(self):
        pass
