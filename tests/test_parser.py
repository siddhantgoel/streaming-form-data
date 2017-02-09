from unittest import TestCase

from requests_toolbelt import MultipartEncoder
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.delegates import ValueDelegate
from streaming_form_data.part import Part


class StreamingFormDataParserTestCase(TestCase):
    def test_smoke(self):
        encoder = MultipartEncoder(fields={'name': 'hello'})

        parser = StreamingFormDataParser(
            expected_parts=(), headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

    def test_basic(self):
        delegate = ValueDelegate()
        expected_parts = (Part('value', delegate),)

        encoder = MultipartEncoder(fields={'value': 'hello world'})

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(delegate.value, b'hello world')

    def test_multiple(self):
        first = ValueDelegate()
        second = ValueDelegate()
        third = ValueDelegate()

        expected_parts = (
            Part('first', first),
            Part('second', second),
            Part('third', third),
        )

        encoder = MultipartEncoder(fields={
            'first': 'foo',
            'second': 'bar',
            'third': 'baz'
        })

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(first.value, b'foo')
        self.assertEqual(second.value, b'bar')
        self.assertEqual(third.value, b'baz')
