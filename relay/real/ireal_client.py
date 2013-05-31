class IRealClient(object):
    """This receives the actual proxied data (going toward the client)."""
    
    def receive_data(self, proxied_data):
        raise NotImplementedError()

    def ready(self):
        raise NotImplementedError()

    def shutdown(self):
        raise NotImplementedError()
