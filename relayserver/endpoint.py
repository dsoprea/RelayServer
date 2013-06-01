from struct import unpack
from threading import Lock

from relayserver.base_protocol import BaseProtocol


class EndpointBaseProtocol(BaseProtocol):
    __locker = Lock()

    def __init__(self):
        self.__buffer = ""
    
    def push_data(self, data):
        """Data has been received while we are still in an unconfigured state. 
        Push all data until we can see a complete message.
        """
        
        with self.__class__.__locker:
            self.__buffer += data
    
    def get_and_clear_buffer(self):
        """This is called every time we receive data, but it's only really of 
        use immediately following being configured, just in case we pushed any 
        data that came in right behind the initial message."""
        
        with self.__class__.__locker:
            buffer_ = self.__buffer
            self.__buffer = ""

        return buffer_
    
    def get_initial_message(self):
        """We expect exactly one message within the entire session. Return None 
        if not found.
        """

        length_length = 4
        current_bytes = len(self.__buffer)
        if current_bytes < length_length:
            return None

        length_bytes = self.__buffer[0:length_length]
        (length,) = unpack('>I', length_bytes)

        if current_bytes < (length_length + length):
            return None
            
        message = self.__buffer[length_length:(length_length + length)]
        self.__buffer = self.__buffer[(length_length + length):]

        return message
