from random import randrange
from datetime import datetime

from relay.real.ireal_client import IRealClient


class HvClient(IRealClient):
    """This receives the actual proxied data."""
    
    __data_char = 'x'
    __eol_char = 'y'
    
    def __init__(self, connection):
        self.__connection = connection
        self.__start_dt = datetime.now()
        self.__count = 0
        self.__conversations = 0
        self.__max_conversations = 100 #randrange(100, 1000)

    def __send_random_data(self):
        
        i = 5000 #randrange(5000, 50000)
        data = self.__class__.__data_char * i + self.__class__.__eol_char

        self.__conversations += 1
        self.__count += len(data)

        self.__connection.transport.write(data)

    def receive_data(self, proxied_data):
        # If we've hit out limit, kill the connection.
        if self.__conversations >= self.__max_conversations:
            self.__connection.transport.loseConnection()
            return

        if self.__class__.__eol_char in proxied_data:
            self.__send_random_data()

    def ready(self):
        self.__send_random_data()

    def shutdown(self):
        now_dt = datetime.now()
        secs = (now_dt - self.__start_dt).total_seconds()
        total_kb = self.__count / 1024
        
        print("HvClient shutting down.\n"
              "\tMessages sent: (%d)\n"
              "\tKilobytes sent: (%.1f)\n"
              "\tTime alive (s): %d (%s - %s)\n" % 
              (self.__conversations,
               total_kb, 
               secs, now_dt, self.__start_dt))
