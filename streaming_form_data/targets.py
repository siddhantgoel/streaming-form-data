import hashlib


class BaseTarget(object):
    """Targets determine what to do with some input once the parser is done with
    it. Any new Target should inherit from this class and override
    data_received.
    """

    def start(self):
        pass

    def data_received(self, chunk):
        raise NotImplementedError()

    def finish(self):
        pass


class NullTarget(BaseTarget):
    def data_received(self, chunk):
        pass


class ValueTarget(BaseTarget):
    def __init__(self):
        self._values = []

    def data_received(self, chunk):
        self._values.append(chunk)

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
        self._fd.flush()
        self._fd.close()


class SHA256Target(BaseTarget):
    def __init__(self):
        self._hash = hashlib.sha256()

    def data_received(self, chunk):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()
