class Part(object):
    """One part of a multipart/form-data request
    """

    def __init__(self, name, target):
        self.name = name
        self.target = target

        self._reading = False

    def start(self):
        self._reading = True
        self.target.start()

    def data_received(self, chunk):
        self.target.data_received(chunk)

    def finish(self):
        self._reading = False
        self.target.finish()

    @property
    def is_reading(self):
        return self._reading
