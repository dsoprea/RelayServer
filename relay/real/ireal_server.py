class IRealServer(object):
    """This receives the actual proxied data (going toward the server)."""
        
    def receive_data(self, proxied_data):
        raise NotImplementedError()

    def shutdown(self):
        raise NotImplementedError()
