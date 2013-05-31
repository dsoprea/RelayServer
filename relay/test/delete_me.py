from message_types.hello_pb2 import Hello, HostProcessHelloResponse,\
                                    ClientHelloResponse, HostProcessHelloProperties
from message_types.command_pb2 import Command,\
                                      ClientConnectionOpenProperties,\
                                      ClientConnectionDropProperties
        
#properties = HostProcessHelloProperties()

hello = Hello()
hello.version = 1
hello.peer_type = Hello.HOST_PROCESS
#hello.hostprocess_properties.test = 55# = properties

inited = hello.hostprocess_properties.IsInitialized()
inited = hello.IsInitialized()

flat = hello.SerializeToString()

restored = Hello()
restored.ParseFromString(flat)

inited = restored.IsInitialized()

aa = 5
