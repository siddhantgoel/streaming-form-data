import hashlib
import asyncio
from pathlib import Path
from typing import Callable, List, Optional, Union

import smart_open  # type: ignore
import aiofiles

class BaseTarget:
    """
    Targets determine what to do with some input once the parser is done processing it.
    Any new Target should inherit from this base class and override the `data_received`
    method.
    """

    def __init__(self, validator: Optional[Callable] = None):
        self.multipart_filename: Optional[str] = None
        self.multipart_content_type: Optional[str] = None

        self._started = False
        self._finished = False
        self._validator = validator

    def _validate(self, chunk: bytes):
        if self._validator:
            self._validator(chunk)

    def start(self):
        self._started = True
        self.on_start()

    def on_start(self):
        pass

    def data_received(self, chunk: bytes):
        self._validate(chunk)
        self.on_data_received(chunk)

    def on_data_received(self, chunk: bytes):
        raise NotImplementedError()

    def finish(self):
        self.on_finish()
        self._finished = True

    def on_finish(self):
        pass

    def set_multipart_filename(self, filename: str):
        self.multipart_filename = filename

    def set_multipart_content_type(self, content_type: str):
        self.multipart_content_type = content_type


class BaseAsyncTarget(BaseTarget):
    """
    Async version of BaseTarget.
    """
    async def start(self):
        self._started = True
        await self.on_start()

    async def on_start(self):
        pass

    async def data_received(self, chunk: bytes):
        self._validate(chunk)
        await self.on_data_received(chunk)

    async def on_data_received(self, chunk: bytes):
        raise NotImplementedError()

    async def finish(self):
        await self.on_finish()
        self._finished = True

    async def on_finish(self):
        pass


class MultipleTargets(BaseTarget):
    def __init__(self, next_target: Callable):
        self._next_target = next_target
        self.targets: List[BaseTarget] = []
        self._validator = None
        self._next_multipart_filename: Optional[str] = None
        self._next_multipart_content_type: Optional[str] = None

    def on_start(self):
        target = self._next_target()
        if self._next_multipart_filename is not None:
            target.set_multipart_filename(self._next_multipart_filename)
            self._next_multipart_filename = None
        if self._next_multipart_content_type is not None:
            target.set_multipart_filename(self._next_multipart_content_type)
            self._next_multipart_content_type = None

        self.targets.append(target)
        target.start()

    def on_data_received(self, chunk: bytes):
        self.targets[-1].data_received(chunk)

    def on_finish(self):
        self.targets[-1].finish()

    def set_multipart_filename(self, filename: str):
        self._next_multipart_filename = filename

    def set_multipart_content_type(self, content_type: str):
        self._next_multipart_content_type = content_type


class AsyncMultipleTargets(BaseAsyncTarget):
    def __init__(self, next_target: Callable):
        super().__init__()
        self._next_target = next_target
        self.targets: List[BaseAsyncTarget] = []
        self._validator = None
        self._next_multipart_filename: Optional[str] = None
        self._next_multipart_content_type: Optional[str] = None

    async def on_start(self):
        target = self._next_target()
        if self._next_multipart_filename is not None:
            target.set_multipart_filename(self._next_multipart_filename)
            self._next_multipart_filename = None
        if self._next_multipart_content_type is not None:
            target.set_multipart_filename(self._next_multipart_content_type)
            self._next_multipart_content_type = None

        self.targets.append(target)
        await target.start()

    async def on_data_received(self, chunk: bytes):
        await self.targets[-1].data_received(chunk)

    async def on_finish(self):
        await self.targets[-1].finish()

    def set_multipart_filename(self, filename: str):
        self._next_multipart_filename = filename

    def set_multipart_content_type(self, content_type: str):
        self._next_multipart_content_type = content_type


class NullTarget(BaseTarget):
    def on_data_received(self, chunk: bytes):
        pass


class AsyncNullTarget(BaseAsyncTarget):
    async def on_data_received(self, chunk: bytes):
        pass


class ValueTarget(BaseTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values = []

    def on_data_received(self, chunk: bytes):
        self._values.append(chunk)

    @property
    def value(self):
        return b"".join(self._values)


class AsyncValueTarget(BaseAsyncTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values = []

    async def on_data_received(self, chunk: bytes):
        self._values.append(chunk)

    @property
    def value(self):
        return b"".join(self._values)


class ListTarget(BaseTarget):
    def __init__(self, _type=bytes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_value = []
        self._values = []
        self._type = _type

    def on_data_received(self, chunk: bytes):
        self._temp_value.append(chunk)

    def on_finish(self):
        value = b"".join(self._temp_value)
        self._temp_value = []
        if self._type is str:
            value = value.decode("UTF-8")
        elif self._type is bytes:
            pass
        else:
            value = self._type(value)
        self._values.append(value)

    @property
    def value(self):
        return self._values

    @property
    def finished(self):
        return self._finished


class AsyncListTarget(BaseAsyncTarget):
    def __init__(self, _type=bytes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_value = []
        self._values = []
        self._type = _type

    async def on_data_received(self, chunk: bytes):
        self._temp_value.append(chunk)

    async def on_finish(self):
        value = b"".join(self._temp_value)
        self._temp_value = []
        if self._type is str:
            value = value.decode("UTF-8")
        elif self._type is bytes:
            pass
        else:
            value = self._type(value)
        self._values.append(value)

    @property
    def value(self):
        return self._values

    @property
    def finished(self):
        return self._finished


class FileTarget(BaseTarget):
    def __init__(
        self,
        filename: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.filename = filename() if callable(filename) else filename
        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None

    def on_start(self):
        self._fd = open(self.filename, self._mode)

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        if self._fd:
            self._fd.close()


class AsyncFileTarget(BaseAsyncTarget):
    def __init__(
        self,
        filename: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.filename = filename() if callable(filename) else filename
        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None

    async def on_start(self):
        self._fd = await aiofiles.open(self.filename, self._mode)

    async def on_data_received(self, chunk: bytes):
        if self._fd:
            await self._fd.write(chunk)

    async def on_finish(self):
        if self._fd:
            await self._fd.close()


class DirectoryTarget(BaseTarget):
    def __init__(
        self,
        directory_path: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.directory_path = (
            directory_path() if callable(directory_path) else directory_path
        )
        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None
        self.multipart_filenames: List[str] = []
        self.multipart_content_types: List[str] = []

    def on_start(self):
        if not self.multipart_filename:
            return
        self.multipart_filename = Path(self.multipart_filename).resolve().name
        self._fd = open(Path(self.directory_path) / self.multipart_filename, self._mode)

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        self.multipart_filenames.append(self.multipart_filename)
        self.multipart_content_types.append(self.multipart_content_type)
        if self._fd:
            self._fd.close()


class AsyncDirectoryTarget(BaseAsyncTarget):
    def __init__(
        self,
        directory_path: Union[str, Callable],
        allow_overwrite: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.directory_path = (
            directory_path() if callable(directory_path) else directory_path
        )
        self._mode = "wb" if allow_overwrite else "xb"
        self._fd = None
        self.multipart_filenames: List[str] = []
        self.multipart_content_types: List[str] = []

    async def on_start(self):
        if not self.multipart_filename:
            return
        self.multipart_filename = Path(self.multipart_filename).resolve().name
        self._fd = await aiofiles.open(Path(self.directory_path) / self.multipart_filename, self._mode)

    async def on_data_received(self, chunk: bytes):
        if self._fd:
            await self._fd.write(chunk)

    async def on_finish(self):
        self.multipart_filenames.append(self.multipart_filename)
        self.multipart_content_types.append(self.multipart_content_type)
        if self._fd:
            await self._fd.close()


class SHA256Target(BaseTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hash = hashlib.sha256()

    def on_data_received(self, chunk: bytes):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()


class AsyncSHA256Target(BaseAsyncTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hash = hashlib.sha256()

    async def on_data_received(self, chunk: bytes):
        self._hash.update(chunk)

    @property
    def value(self):
        return self._hash.hexdigest()


class SmartOpenTarget(BaseTarget):
    def __init__(
        self,
        file_path: Union[str, Callable],
        mode: str,
        transport_params=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._file_path = file_path() if callable(file_path) else file_path
        self._mode = mode
        self._transport_params = transport_params
        self._fd = None

    def on_start(self):
        self._fd = smart_open.open(
            self._file_path,
            self._mode,
            transport_params=self._transport_params,
        )

    def on_data_received(self, chunk: bytes):
        if self._fd:
            self._fd.write(chunk)

    def on_finish(self):
        if self._fd:
            self._fd.close()


class AsyncSmartOpenTarget(BaseAsyncTarget):
    def __init__(
        self,
        file_path: Union[str, Callable],
        mode: str,
        transport_params=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._file_path = file_path() if callable(file_path) else file_path
        self._mode = mode
        self._transport_params = transport_params
        self._fd = None

    async def on_start(self):
        loop = asyncio.get_running_loop()
        self._fd = await loop.run_in_executor(
            None,
            lambda: smart_open.open(
                self._file_path,
                self._mode,
                transport_params=self._transport_params,
            )
        )

    async def on_data_received(self, chunk: bytes):
        if self._fd:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._fd.write, chunk)

    async def on_finish(self):
        if self._fd:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._fd.close)


class S3Target(SmartOpenTarget):
    pass

class GCSTarget(SmartOpenTarget):
    pass

class AsyncS3Target(AsyncSmartOpenTarget):
    pass

class AsyncGCSTarget(AsyncSmartOpenTarget):
    pass


class CSVTarget(BaseTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lines = []
        self._previous_partial_line = ""

    def on_data_received(self, chunk: bytes):
        combined = self._previous_partial_line + chunk.decode("utf-8")
        lines = combined.splitlines(keepends=True)
        for line in lines[:-1]:
            self._lines.append(line.replace("\n", ""))
        if lines[-1].endswith("\n"):
            self._lines.append(lines[-1].replace("\n", ""))
            self._previous_partial_line = ""
        else:
            self._previous_partial_line = lines[-1]

    def pop_lines(self, include_partial_line: bool = False):
        lines = self._lines
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
            self._previous_partial_line = ""
        self._lines = []
        return lines

    def get_lines(self, include_partial_line: bool = False):
        lines = self._lines.copy()
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
        return lines


class AsyncCSVTarget(BaseAsyncTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lines = []
        self._previous_partial_line = ""

    async def on_data_received(self, chunk: bytes):
        combined = self._previous_partial_line + chunk.decode("utf-8")
        lines = combined.splitlines(keepends=True)
        for line in lines[:-1]:
            self._lines.append(line.replace("\n", ""))
        if lines[-1].endswith("\n"):
            self._lines.append(lines[-1].replace("\n", ""))
            self._previous_partial_line = ""
        else:
            self._previous_partial_line = lines[-1]

    def pop_lines(self, include_partial_line: bool = False):
        lines = self._lines
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
            self._previous_partial_line = ""
        self._lines = []
        return lines

    def get_lines(self, include_partial_line: bool = False):
        lines = self._lines.copy()
        if include_partial_line and self._previous_partial_line:
            lines.append(self._previous_partial_line)
        return lines