import os.path
from unittest import TestCase

from requests_toolbelt import MultipartEncoder
from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget
from streaming_form_data.part import Part


DATA_DIR = 'tests/data'


def data_file_path(filename):
    return os.path.join(DATA_DIR, filename)


def load_file(path):
    _, filename = os.path.split(path)

    with open(path, 'rb') as file_:
        fields = {
            filename: (filename, file_, 'text/plain')
        }

        encoder = MultipartEncoder(fields=fields)

        return (encoder.content_type, encoder.to_string())


class StreamingFormDataParserTestCase(TestCase):
    def test_smoke(self):
        encoder = MultipartEncoder(fields={'name': 'hello'})

        parser = StreamingFormDataParser(
            expected_parts=(), headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

    def test_basic_single(self):
        target = ValueTarget()
        expected_parts = (Part('value', target),)

        encoder = MultipartEncoder(fields={'value': 'hello world'})

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello world')

    def test_basic_multiple(self):
        first = ValueTarget()
        second = ValueTarget()
        third = ValueTarget()

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
        expected_value = 'hello world'

        target = ValueTarget()
        expected_parts = (Part('value', target),)

        encoder = MultipartEncoder(fields={'value': expected_value})

        body = encoder.to_string()

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})

        index = body.index(b'world')

        parser.data_received(body[:index])
        parser.data_received(body[index:])

        self.assertEqual(target.value, expected_value.encode('utf-8'))

    def test_chunked_multiple(self):
        expected_first_value = 'foo' * 1000
        expected_second_value = 'bar' * 1000
        expected_third_value = 'baz' * 1000

        first = ValueTarget()
        second = ValueTarget()
        third = ValueTarget()

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
        size = 100

        while len(body):
            chunks.append(body[:size])
            body = body[size:]

        for chunk in chunks:
            parser.data_received(chunk)

        self.assertEqual(first.value, expected_first_value.encode('utf-8'))
        self.assertEqual(second.value, expected_second_value.encode('utf-8'))
        self.assertEqual(third.value, expected_third_value.encode('utf-8'))

    def test_break_chunk_at_boundary(self):
        expected_first_value = 'hello' * 500
        expected_second_value = 'hello' * 500

        first = ValueTarget()
        second = ValueTarget()

        expected_parts = (
            Part('first', first),
            Part('second', second),
        )

        encoder = MultipartEncoder(fields={
            'first': 'hello' * 500,
            'second': 'hello' * 500
        })

        body = encoder.to_string()
        boundary = encoder.boundary.encode('utf-8')

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})

        index = body[50:].index(boundary) + 5

        parser.data_received(body[:index])
        parser.data_received(body[index:])

        self.assertEqual(first.value, expected_first_value.encode('utf-8'))
        self.assertEqual(second.value, expected_second_value.encode('utf-8'))

    def test_file_content_single(self):
        filenames = ('file.txt', 'image-600x400.png', 'image-2560x1600.png')

        for filename in filenames:
            with open(data_file_path(filename), 'rb') as file_:
                expected_value = file_.read()

            content_type, body = load_file(data_file_path(filename))

            value = ValueTarget()

            expected_parts = (Part(filename, value),)

            parser = StreamingFormDataParser(
                expected_parts=expected_parts,
                headers={'Content-Type': content_type})

            parser.data_received(body)

            self.assertEqual(value.value, expected_value)

    def test_file_content_multiple(self):
        with open(data_file_path('file.txt'), 'rb') as file_:
            expected_value = file_.read()

        content_type, body = load_file(data_file_path('file.txt'))

        txt = ValueTarget()

        expected_parts = (Part('file.txt', txt),)

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': content_type})

        size = 50
        chunks = []

        while body:
            chunks.append(body[:size])
            body = body[size:]

        for chunk in chunks:
            parser.data_received(chunk)

        self.assertEqual(txt.value, expected_value)

    def test_file_content_varying_chunk_size(self):
        with open(data_file_path('file.txt'), 'rb') as file_:
            expected_value = file_.read()

        content_type, body = load_file(data_file_path('file.txt'))

        for index in range(len(body)):
            txt = ValueTarget()

            expected_parts = (Part('file.txt', txt),)

            parser = StreamingFormDataParser(
                expected_parts=expected_parts,
                headers={'Content-Type': content_type})

            parser.data_received(body[:index])
            parser.data_received(body[index:])

            self.assertEqual(txt.value, expected_value)

    def test_mixed_content_varying_chunk_size(self):
        with open(data_file_path('file.txt'), 'rb') as file_:
            expected_value = file_.read()

        with open(data_file_path('file.txt'), 'rb') as file_:
            fields = {
                'name': 'hello world',
                'age': '10',
                'cv.txt': ('file.txt', file_, 'text/plain')
            }

            encoder = MultipartEncoder(fields=fields)

            body = encoder.to_string()
            content_type = encoder.content_type

        for index in range(len(body)):
            name = ValueTarget()
            age = ValueTarget()
            cv = ValueTarget()

            expected_parts = (
                Part('name', name),
                Part('age', age),
                Part('cv.txt', cv),
            )

            parser = StreamingFormDataParser(
                expected_parts=expected_parts,
                headers={'Content-Type': content_type})

            parser.data_received(body[:index])
            parser.data_received(body[index:])

            self.assertEqual(name.value, b'hello world')
            self.assertEqual(age.value, b'10')
            self.assertEqual(cv.value, expected_value)

    def test_parameter_contains_crlf(self):
        target = ValueTarget()
        expected_parts = (Part('value', target),)

        encoder = MultipartEncoder(fields={'value': 'hello\r\nworld'})

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello\r\nworld')

    def test_parameter_ends_with_crlf(self):
        target = ValueTarget()
        expected_parts = (Part('value', target),)

        encoder = MultipartEncoder(fields={'value': 'hello\r\n'})

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello\r\n')

    def test_parameter_starts_with_crlf(self):
        target = ValueTarget()
        expected_parts = (Part('value', target),)

        encoder = MultipartEncoder(fields={'value': '\r\nworld'})

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'\r\nworld')

    def test_multiple_files(self):
        txt_filename = 'file.txt'
        png_filename = 'image-600x400.png'

        with open(data_file_path(txt_filename), 'rb') as file_:
            expected_txt = file_.read()

        with open(data_file_path(png_filename), 'rb') as file_:
            expected_png = file_.read()

        txt_target = ValueTarget()
        png_target = ValueTarget()

        with open(data_file_path(txt_filename), 'rb') as txt_file, \
                open(data_file_path(png_filename), 'rb') as png_file:
            encoder = MultipartEncoder(fields={
                txt_filename: (txt_filename, txt_file,
                               'application/plain'),
                png_filename: (png_filename, png_file, 'image/png')
            })

            expected_parts = (
                Part(txt_filename, txt_target),
                Part(png_filename, png_target),
            )

            parser = StreamingFormDataParser(
                expected_parts=expected_parts,
                headers={'Content-Type': encoder.content_type})
            parser.data_received(encoder.to_string())

            self.assertEqual(txt_target.value, expected_txt)
            self.assertEqual(png_target.value, expected_png)

    def test_large_file(self):
        filename = 'image-500k.png'

        with open(data_file_path(filename), 'rb') as file_:
            expected_value = file_.read()

        content_type, body = load_file(data_file_path(filename))

        value = ValueTarget()

        expected_parts = (Part(filename, value),)

        parser = StreamingFormDataParser(
            expected_parts=expected_parts,
            headers={'Content-Type': content_type})

        parser.data_received(body)

        self.assertEqual(value.value, expected_value)
