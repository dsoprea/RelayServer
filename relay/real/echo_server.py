from relay.real.ireal_server import IRealServer


class EchoServer(IRealServer):
    def __init__(self, connection):
        self.__connection = connection
        
    def receive_data(self, proxied_data):
        print("Echo server received (%d) bytes: [%s]" % 
                (len(proxied_data), proxied_data))

        print("Echoing.")
        self.__connection.transport.write(proxied_data)

    def shutdown(self):
        pass
