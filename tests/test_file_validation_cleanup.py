import pytest
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget
from streaming_form_data.validators import MaxSizeValidator, ValidationError


@pytest.mark.parametrize("chunk_size", [1, 7, 4096])
def test_file_validation_closes_partial_file(tmp_path, chunk_size):
    target = FileTarget(str(tmp_path / "upload.bin"), validator=MaxSizeValidator(3))
    parser = StreamingFormDataParser(
        {"Content-Type": "multipart/form-data; boundary=example"}
    )
    parser.register("file", target)
    body = (
        b'--example\r\nContent-Disposition: form-data; name="file"; filename="synthetic.bin"\r\n\r\n'
        b"abcdefgh\r\n--example--\r\n"
    )
    try:
        with pytest.raises(ValidationError):
            for start in range(0, len(body), chunk_size):
                parser.data_received(body[start : start + chunk_size])
        assert target._fd is not None
        assert target._fd.closed
        assert not target._finished
    finally:
        if target._fd is not None:
            target._fd.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("chunk_size", [1, 7, 4096])
async def test_file_validation_closes_partial_file_async(tmp_path, chunk_size):
    target = FileTarget(str(tmp_path / "upload.bin"), validator=MaxSizeValidator(3))
    parser = StreamingFormDataParser(
        {"Content-Type": "multipart/form-data; boundary=example"}
    )
    parser.register("file", target)
    body = (
        b'--example\r\nContent-Disposition: form-data; name="file"; filename="synthetic.bin"\r\n\r\n'
        b"abcdefgh\r\n--example--\r\n"
    )
    try:
        with pytest.raises(ValidationError):
            for start in range(0, len(body), chunk_size):
                await parser.adata_received(body[start : start + chunk_size])
        assert target._fd is not None
        assert target._fd.closed
        assert not target._finished
    finally:
        if target._fd is not None:
            await target._fd.close()


@pytest.mark.parametrize("fail", [False, True])
def test_file_error_does_not_finalize(tmp_path, fail):
    failure = ValueError("synthetic validation failure")

    def validate(chunk):
        if fail:
            raise failure

    class Target(FileTarget):
        finalized = False

        def on_finish(self):
            self.finalized = True
            super().on_finish()

    target = Target(str(tmp_path / "upload.bin"), validator=validate)
    target.start()
    try:
        if fail:
            with pytest.raises(ValueError) as caught:
                target.data_received(b"abc")
            assert caught.value is failure
            assert target._fd.closed
            assert not target.finalized
            assert not target._finished
        else:
            target.data_received(b"abc")
            assert not target._fd.closed
            target.finish()
            assert target.finalized
            assert target._finished
            assert (tmp_path / "upload.bin").read_bytes() == b"abc"
    finally:
        target._fd.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_file_error_does_not_finalize_async(tmp_path, fail):
    failure = ValueError("synthetic validation failure")

    def validate(chunk):
        if fail:
            raise failure

    class Target(FileTarget):
        finalized = False

        async def on_finish_async(self):
            self.finalized = True
            await super().on_finish_async()

    target = Target(str(tmp_path / "upload.bin"), validator=validate)
    await target.astart()
    try:
        if fail:
            with pytest.raises(ValueError) as caught:
                await target.adata_received(b"abc")
            assert caught.value is failure
            assert target._fd.closed
            assert not target.finalized
            assert not target._finished
        else:
            await target.adata_received(b"abc")
            assert not target._fd.closed
            await target.afinish()
            assert target.finalized
            assert target._finished
            assert (tmp_path / "upload.bin").read_bytes() == b"abc"
    finally:
        await target._fd.close()


@pytest.mark.parametrize("close_fails", [False, True])
def test_write_failure_preserves_error(close_fails):
    write_error = OSError("synthetic write failure")
    close_error = OSError("synthetic close failure")

    class Writer:
        closed = False

        def write(self, chunk):
            raise write_error

        def close(self):
            self.closed = True
            if close_fails:
                raise close_error

    target = FileTarget("unused")
    target._fd = Writer()
    with pytest.raises(OSError) as caught:
        target.data_received(b"abc")
    assert caught.value is write_error
    assert target._fd.closed
    assert not target._finished
    assert caught.value.__cause__ is (close_error if close_fails else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("close_fails", [False, True])
async def test_write_failure_preserves_error_async(close_fails):
    write_error = OSError("synthetic write failure")
    close_error = OSError("synthetic close failure")

    class Writer:
        closed = False

        async def write(self, chunk):
            raise write_error

        async def close(self):
            self.closed = True
            if close_fails:
                raise close_error

    target = FileTarget("unused")
    target._fd = Writer()
    with pytest.raises(OSError) as caught:
        await target.adata_received(b"abc")
    assert caught.value is write_error
    assert target._fd.closed
    assert not target._finished
    assert caught.value.__cause__ is (close_error if close_fails else None)
