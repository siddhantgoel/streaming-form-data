class BaseTarget(object):
    def start(self):
        raise NotImplementedError()

    def data_received(self, chunk):
        raise NotImplementedError()

    def finish(self):
        raise NotImplementedError()


class NullTarget(BaseTarget):
    def start(self):
        pass

    def data_received(self, chunk):
        pass

    def finish(self):
        pass


class ValueTarget(BaseTarget):
    def __init__(self):
        self._values = []

    def start(self):
        pass

    def data_received(self, chunk):
        self._values.append(chunk)

    def finish(self):
        pass

    @property
    def value(self):
        return b''.join(self._values)


class FileTarget(BaseTarget):
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
