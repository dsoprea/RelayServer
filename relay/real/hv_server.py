from datetime import datetime

from relay.real.ireal_server import IRealServer


class HvServer(IRealServer):
    """This receives a high-volume of data (for testing)."""
    
    __eol_char = 'y'

    def __init__(self, connection):
        self.__connection = connection
        self.__start_dt = datetime.now()
        self.__count = 0
        self.__conversations = 0
        self.__buffers = []
        
    def receive_data(self, proxied_data):
        self.__count += len(proxied_data)
        self.__buffers.append(proxied_data)

        if self.__class__.__eol_char in proxied_data:
            # We've seen the end of the message. Now, send it back.
            
            self.__conversations += 1
            contiguous = ''.join(self.__buffers)
            self.__buffers = []

            self.__connection.transport.write(contiguous)

    def shutdown(self):
        now_dt = datetime.now()
        secs = (now_dt - self.__start_dt).total_seconds()
        total_kb = self.__count / 1024
        
        print("HvServer shutting down.\n"
              "\tMessages echo'd: (%d)\n"
              "\tKilobytes echo'd: (%.1f)\n"
              "\tTime alive (s): %d (%s - %s)\n" % 
              (self.__conversations,
               total_kb, 
               secs, now_dt, self.__start_dt))
