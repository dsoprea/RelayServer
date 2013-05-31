from random import randrange
from datetime import datetime
from twisted.python import log

from relay.real.ireal_client import IRealClient


class HvClient(IRealClient):
    """This receives the actual proxied data."""
    
    def __init__(self, connection):
        self.__connection = connection
        self.__count = 0
        self.__cycles = randrange(100, 1000)
        self.__start_dt = datetime.now()

    def __send_random_data(self):
        
        self.__cycles -= 1

        i = randrange(5000, 50000)
        data = 'x' * i
        self.__connection.transport.write(data)
        
    def receive_data(self, proxied_data):
        self.__count += len(proxied_data)

        # If we've hit out limit, kill the connection.
        if self.__cycles <= 0:
            self.__connection.transport.loseConnection()
            return

        self.__send_random_data()

    def ready(self):
        self.__send_random_data()

    def shutdown(self):
        secs = (datetime.now() - self.__start_dt).total_seconds()
        
        print("HvClient shutting down with a byte count of (%d) and average "
              "rate of (%d)/s." % (self.__count, self.__count / secs))
