from twisted.python import log
from datetime import datetime

from relay.real.ireal_server import IRealServer


class HvServer(IRealServer):
    """This receives a high-volume of data (for testing)."""
    
    def __init__(self, connection):
        self.__connection = connection
        self.__count = 0
        self.__start_dt = datetime.now()
        
    def receive_data(self, proxied_data):
        self.__count += len(proxied_data)

        self.__connection.transport.write(proxied_data)

    def shutdown(self):
        secs = (datetime.now() - self.__start_dt).total_seconds()
        
        print("HvServer with session-no (%d) shutting down with a byte count "
              "of (%d) and average rate of (%d)/s." % 
              (self.__connection.session_no, self.__count, 
               self.__count / secs))
