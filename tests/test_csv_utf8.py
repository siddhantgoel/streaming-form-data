import pytest

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import CSVTarget


CASES = [
    (char, split)
    for char in ["é", "東", "🌍"]
    for split in range(1, len(char.encode("utf-8")) + 1)
]


def multipart_chunks(char, split):
    # Cross the parser's minimum body-chunk size before splitting a character.
    prefix = "x" * 1024 + ","
    encoded = char.encode("utf-8")
    return [
        b'--example\r\nContent-Disposition: form-data; name="file"; filename="synthetic.csv"\r\n\r\n',
        prefix.encode() + encoded[:split],
        encoded[split:] + b"\n\r\n--example--\r\n",
    ], prefix + char


@pytest.mark.parametrize("char,split", CASES)
def test_csv_utf8_multipart_chunks(char, split):
    target = CSVTarget()
    parser = StreamingFormDataParser(
        {"Content-Type": "multipart/form-data; boundary=example"}
    )
    parser.register("file", target)
    chunks, expected = multipart_chunks(char, split)
    lines = []
    for chunk in chunks:
        parser.data_received(chunk)
        lines.extend(target.pop_lines())
    assert lines == [expected]
    assert target.get_lines(include_partial_line=True) == []
    assert target._finished


@pytest.mark.asyncio
@pytest.mark.parametrize("char,split", CASES)
async def test_csv_utf8_multipart_chunks_async(char, split):
    target = CSVTarget()
    parser = StreamingFormDataParser(
        {"Content-Type": "multipart/form-data; boundary=example"}
    )
    parser.register("file", target)
    chunks, expected = multipart_chunks(char, split)
    lines = []
    for chunk in chunks:
        await parser.adata_received(chunk)
        lines.extend(target.pop_lines())
    assert lines == [expected]
    assert target.get_lines(include_partial_line=True) == []
    assert target._finished


def test_csv_utf8_partial_line_and_empty_chunks():
    target = CSVTarget()
    target.start()
    target.data_received(b"first\nsecond,")
    target.data_received(b"")
    target.data_received(b"\xf0\x9f")
    assert target.pop_lines() == ["first"]
    assert target.get_lines(include_partial_line=True) == ["second,"]
    target.data_received(b"\x8c\x8d")
    target.finish()
    assert target.pop_lines() == []
    assert target.pop_lines(include_partial_line=True) == ["second,🌍"]


@pytest.mark.asyncio
async def test_csv_utf8_partial_line_and_empty_chunks_async():
    target = CSVTarget()
    await target.astart()
    await target.adata_received(b"first\nsecond,")
    await target.adata_received(b"")
    await target.adata_received(b"\xf0\x9f")
    assert target.pop_lines() == ["first"]
    assert target.get_lines(include_partial_line=True) == ["second,"]
    await target.adata_received(b"\x8c\x8d")
    await target.afinish()
    assert target.pop_lines() == []
    assert target.pop_lines(include_partial_line=True) == ["second,🌍"]


@pytest.mark.parametrize("invalid", [b"\xff", b"\xc3\x28"])
def test_csv_utf8_rejects_invalid_data(invalid):
    target = CSVTarget()
    target.start()
    with pytest.raises(UnicodeDecodeError):
        target.data_received(invalid)


@pytest.mark.parametrize("incomplete", [b"\xc3", b"\xe6\x9d", b"\xf0\x9f\x8c"])
def test_csv_utf8_rejects_incomplete_final_character(incomplete):
    target = CSVTarget()
    target.start()
    target.data_received(incomplete)
    with pytest.raises(UnicodeDecodeError):
        target.finish()
    assert not target._finished
    target.start()
    target.data_received(b"new part\n")
    target.finish()
    assert target.pop_lines() == ["new part"]


@pytest.mark.asyncio
@pytest.mark.parametrize("incomplete", [b"\xc3", b"\xe6\x9d", b"\xf0\x9f\x8c"])
async def test_csv_utf8_rejects_incomplete_final_character_async(incomplete):
    target = CSVTarget()
    await target.astart()
    await target.adata_received(incomplete)
    with pytest.raises(UnicodeDecodeError):
        await target.afinish()
    assert not target._finished
    await target.astart()
    await target.adata_received(b"new part\n")
    await target.afinish()
    assert target.pop_lines() == ["new part"]
