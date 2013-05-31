from struct import pack
from google.protobuf.message import DecodeError
from twisted.internet.protocol import Protocol


class BaseProtocol(Protocol):
    def write_message(self, message):
        data = message.SerializeToString()
        prefix = pack('>I', len(data))
    
        self.transport.write(prefix)
        self.transport.write(data)

    def parse_or_raise(self, message_raw, type_):
        message = type_()
        
        try:
            message.ParseFromString(message_raw)
        except DecodeError:
            raise
        else:
            if message.IsInitialized() is False:
                raise Exception("Message parse with type [%s] resulted in "
                                "uninitialized message." % (type_))

        return message
