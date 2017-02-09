class Part(object):
    """A part of of multipart/form-data request
    """

    def __init__(self, name, delegate):
        self.name = name
        self.delegate = delegate

        self._reading = False

    def start(self):
        self._reading = True
        self.delegate.start()

    def data_received(self, chunk):
        self.delegate.data_received(chunk)

    def finish(self):
        self._reading = False
        self.delegate.finish()

    @property
    def is_reading(self):
        return self._reading
