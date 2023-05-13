import pytest

from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget


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
