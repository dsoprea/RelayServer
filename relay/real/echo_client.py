from datetime import datetime
from time import sleep

from relay.real.ireal_client import IRealClient


class EchoClient(IRealClient):
    def __init__(self, connection):
        self.__connection = connection

    def __send_test(self):
        self.__connection.transport.write("Test from client: %s" % 
                                          (datetime.now()))
        
    def receive_data(self, proxied_data):
        print("Echo client received (%d) bytes: [%s]" % 
                (len(proxied_data), proxied_data))

        sleep(1)
        self.__send_test()

    def ready(self):
        print("Echo client has been sent the ready signal.")
        
        self.__send_test()

    def shutdown(self):
        pass
