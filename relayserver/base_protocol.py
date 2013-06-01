from struct import pack
from google.protobuf.message import DecodeError
from twisted.internet.protocol import Protocol
from twisted.python import log

from relayserver.utility import get_hex_dump

class BaseProtocol(Protocol):
    def write_message(self, message):
        data = message.SerializeToString()
        message_len = len(data)
        prefix = pack('>I', message_len)
        
        total_len = len(prefix) + message_len
    
        log.msg("Message type [%s] serialized into (%d) bytes and wrapped as "
                "(%d) bytes." % 
                (message.__class__.__name__, message_len, total_len))

        self.transport.write(prefix)
        self.transport.write(data)

    def parse_or_raise(self, message_raw, type_):
        log.msg("Parsing [%s] in (%d) bytes." % (type_.__name__, len(message_raw)))

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

