import hashlib


class BaseTarget:
    """Targets determine what to do with some input once the parser is done with
    it. Any new Target should inherit from this class and override
    data_received.
    """

    def __init__(self):
        self.multipart_filename = None

    # 'multipart_filename ' is filled before start() call.
    # It contains optional 'filename' value from 'Content-Disposition' header
    # Default value is None in case 'filename' is not present.
    #
    # NOTE! You should be very careful with this value
    #       because it comes from the user.
    #       You should never use it without filtering
    #       to construct filename on disk.
    #
    #       Example library for filtering user strings
    #       for use in URLs, filenames:
    #       https://github.com/un33k/python-slugify

    def start(self):
        pass

    def data_received(self, chunk):
        raise NotImplementedError()

    def finish(self):
        pass


class NullTarget(BaseTarget):
    def __init__(self):
        super().__init__()

    def data_received(self, chunk):
        pass


class ValueTarget(BaseTarget):
    def __init__(self):
        super().__init__()
        self._values = []

    def data_received(self, chunk):
        self._values.append(chunk)

    @property
    def value(self):
        return b''.join(self._values)


class FileTarget(BaseTarget):
    def __init__(self, filename, allow_overwrite=True):
        super().__init__()
        self.filename = filename

        self._openmode = 'wb' if allow_overwrite else 'xb'
        self._fd = None

    def start(self):
        self._fd = open(self.filename, self._openmode)

    def data_received(self, chunk):
        self._fd.write(chunk)

    def finish(self):
        self._fd.close()


class SHA256Target(BaseTarget):
    def __init__(self):
        super().__init__()
        self._hash = hashlib.sha256()

    def data_received(self, chunk):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()
