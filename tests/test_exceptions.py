from unittest import TestCase

from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget


def simple_python_function(chunk):
    raise ValueError('CustomTarget exception')


class ExceptionTestCase(TestCase):
    def test_basic_single(self):
        self.assertRaises(ValueError, simple_python_function, "abcd")


class CustomTarget(ValueTarget):
    def data_received(self, chunk):
        raise ValueError('CustomTarget exception')


class ParserTargetExceptionTestCase(TestCase):
    def test_basic_single(self):
        target = CustomTarget()

        encoder = MultipartEncoder(fields={'value': 'hello world'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)

        data = encoder.to_string()

        self.assertRaises(ValueError, parser.data_received, data)
