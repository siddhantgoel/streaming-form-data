class BaseDelegate(object):
    def start(self):
        raise NotImplementedError()

    def data_received(self, chunk):
        raise NotImplementedError()

    def finish(self):
        raise NotImplementedError()


class ValueDelegate(BaseDelegate):
    def __init__(self):
        self._value = None

    def start(self):
        pass

    def data_received(self, chunk):
        self._value = chunk

    def finish(self):
        pass

    @property
    def value(self):
        return self._value


class FileDelegate(BaseDelegate):
    def __init__(self, filename):
        self.filename = filename

        self._fd = None

    def start(self):
        self._fd = open(self.filename, 'wb')

    def data_received(self, chunk):
        self._fd.write(chunk)
        self._fd.flush()

    def finish(self):
        self._fd.close()
