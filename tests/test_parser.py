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

    def test_chunked_single(self):
        expected_value = 'hello' * 5000

        delegate = ValueDelegate()
        expected_parts = (Part('value', delegate),)

        encoder = MultipartEncoder(fields={'value': expected_value})

        body = encoder.to_string()

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})

        chunks = []
        size = 500

        while len(body):
            chunks.append(body[:size])
            body = body[size:]

        for chunk in chunks:
            parser.data_received(chunk)

        self.assertEqual(delegate.value, expected_value.encode('utf-8'))

    def test_chunked_multiple(self):
        expected_first_value = 'foo' * 5000
        expected_second_value = 'bar' * 5000
        expected_third_value = 'baz' * 5000

        first = ValueDelegate()
        second = ValueDelegate()
        third = ValueDelegate()

        expected_parts = (
            Part('first', first),
            Part('second', second),
            Part('third', third),
        )

        encoder = MultipartEncoder(fields={
            'first': expected_first_value,
            'second': expected_second_value,
            'third': expected_third_value,
        })

        body = encoder.to_string()

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})

        chunks = []
        size = 500

        while len(body):
            chunks.append(body[:size])
            body = body[size:]

        for chunk in chunks:
            parser.data_received(chunk)

        self.assertEqual(first.value, expected_first_value.encode('utf-8'))
        self.assertEqual(second.value, expected_second_value.encode('utf-8'))
        self.assertEqual(third.value, expected_third_value.encode('utf-8'))
