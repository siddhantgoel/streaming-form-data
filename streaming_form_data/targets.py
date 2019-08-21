import hashlib


class BaseTarget:
    """Targets determine what to do with some input once the parser is done with
    it. Any new Target should inherit from this class and override
    data_received.
    """
    is_async = False

    def __init__(self, validator=None):
        self.multipart_filename = None

        self._started = False
        self._finished = False
        self._validator = validator

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

    def _validate(self, chunk: bytes):
        if self._validator:
            self._validator(chunk)

    def start(self):
        self._started = True
        self.on_start()

    def on_start(self):
        pass

    async def data_received(self, chunk: bytes):
        self._validate(chunk)
        if self.is_async:
            await self.on_data_received(chunk)
        else:
            self.on_data_received(chunk)

    def on_data_received(self, chunk: bytes):
        raise NotImplementedError()

    def finish(self):
        self.on_finish()
        self._finished = True

    def on_finish(self):
        pass


class NullTarget(BaseTarget):
    def on_data_received(self, chunk: bytes):
        pass


class ValueTarget(BaseTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._values = []

    def on_data_received(self, chunk: bytes):
        self._values.append(chunk)

    @property
    def value(self):
        return b''.join(self._values)


class FileTarget(BaseTarget):
    def __init__(self, filename, allow_overwrite=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = filename

        self._mode = 'wb' if allow_overwrite else 'xb'
        self._fd = None

    def on_start(self):
        self._fd = open(self.filename, self._mode)

    def on_data_received(self, chunk: bytes):
        self._fd.write(chunk)

    def on_finish(self):
        self._fd.close()


class SHA256Target(BaseTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._hash = hashlib.sha256()

    def on_data_received(self, chunk: bytes):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()
