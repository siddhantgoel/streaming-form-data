import pytest

from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget
from streaming_form_data.parser import UnexpectedPartException


class CustomTarget(ValueTarget):
    def data_received(self, chunk):
        raise ValueError("CustomTarget exception")


def test_custom_target_exception():
    target = CustomTarget()

    encoder = MultipartEncoder(fields={"value": "hello world"})

    parser = StreamingFormDataParser(headers={"Content-Type": encoder.content_type})
    parser.register("value", target)

    data = encoder.to_string()

    with pytest.raises(ValueError):
        parser.data_received(data)


def test_unexpected_part_exception():
    target = ValueTarget()

    encoder = MultipartEncoder(fields={"value": "hello world", "extra": "field"})

    parser = StreamingFormDataParser(
        headers={"Content-Type": encoder.content_type}, strict=True
    )
    parser.register("value", target)

    data = encoder.to_string()

    with pytest.raises(UnexpectedPartException):
        parser.data_received(data)
