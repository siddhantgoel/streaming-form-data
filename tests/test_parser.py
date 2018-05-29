from io import BytesIO
from numpy import random
from unittest import TestCase

from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser, ParseFailedException
from streaming_form_data.targets import ValueTarget


def get_random_bytes(size, seed):
    random.seed(seed)
    return random.bytes(size)


def open_dataset(filename):
    if filename == 'file.txt':
        filedata = b'this is a txt file\r\n' * 10
    elif filename == 'image-600x400.png':
        filedata = get_random_bytes(1780, 600)
    elif filename == 'image-2560x1600.png':
        filedata = get_random_bytes(11742, 2560)
    elif filename == 'image-500k.png':
        filedata = get_random_bytes(437814, 500)
    elif filename == 'image-high-res.jpg':
        filedata = get_random_bytes(9450866, 945)
    else:
        raise Exception('Unknown file name: ' + filename)
    return BytesIO(filedata)


def encoded_dataset(filename):
    with open_dataset(filename) as dataset_:
        fields = {
            filename: (filename, dataset_, 'text/plain')
        }

        encoder = MultipartEncoder(fields=fields)

        return (encoder.content_type, encoder.to_string())


class StreamingFormDataParserTestCase(TestCase):
    def test_smoke(self):
        encoder = MultipartEncoder(fields={'name': 'hello'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})

        parser.data_received(encoder.to_string())

    def test_basic_single(self):
        target = ValueTarget()

        encoder = MultipartEncoder(fields={'value': 'hello world'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)

        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello world')
        self.assertEqual(target._started, True)
        self.assertEqual(target._finished, True)

    def test_case_insensitive_content_type(self):
        content_type_header = 'Content-Type'

        for header_key in (content_type_header,
                           content_type_header.lower(),
                           content_type_header.upper(),
                           'cOnTeNt-tYPe'):
            target = ValueTarget()

            encoder = MultipartEncoder(fields={'value': 'hello world'})

            parser = StreamingFormDataParser(
                headers={header_key: encoder.content_type})
            parser.register('value', target)

            parser.data_received(encoder.to_string())

            self.assertEqual(target.value, b'hello world')

    def test_missing_content_type(self):
        self.assertRaises(ParseFailedException,
                          StreamingFormDataParser, {})

        headers = {'someheader': 'somevalue'}
        self.assertRaises(ParseFailedException,
                          StreamingFormDataParser, headers)

    def test_incorrect_content_type(self):
        headers = {'Content-Type': 'multipart/mixed; boundary=1234'}
        self.assertRaises(ParseFailedException,
                          StreamingFormDataParser, headers)

        headers = {'Content-Type': 'multipart/form-data'}
        self.assertRaises(ParseFailedException,
                          StreamingFormDataParser, headers)

        headers = {'Content-Type': 'multipart/form-data; delimiter=1234'}
        self.assertRaises(ParseFailedException,
                          StreamingFormDataParser, headers)

    def test_basic_multiple(self):
        first = ValueTarget()
        second = ValueTarget()
        third = ValueTarget()

        encoder = MultipartEncoder(fields={
            'first': 'foo',
            'second': 'bar',
            'third': 'baz'
        })

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})

        parser.register('first', first)
        parser.register('second', second)
        parser.register('third', third)

        parser.data_received(encoder.to_string())

        self.assertEqual(first.value, b'foo')
        self.assertEqual(second.value, b'bar')
        self.assertEqual(third.value, b'baz')

    def test_chunked_single(self):
        expected_value = 'hello world'

        target = ValueTarget()

        encoder = MultipartEncoder(fields={'value': expected_value})

        body = encoder.to_string()

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)

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

        encoder = MultipartEncoder(fields={
            'first': expected_first_value,
            'second': expected_second_value,
            'third': expected_third_value,
        })

        body = encoder.to_string()

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})

        parser.register('first', first)
        parser.register('second', second)
        parser.register('third', third)

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

        encoder = MultipartEncoder(fields={
            'first': 'hello' * 500,
            'second': 'hello' * 500
        })

        body = encoder.to_string()
        boundary = encoder.boundary.encode('utf-8')

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})

        parser.register('first', first)
        parser.register('second', second)

        index = body[50:].index(boundary) + 5

        parser.data_received(body[:index])
        parser.data_received(body[index:])

        self.assertEqual(first.value, expected_first_value.encode('utf-8'))
        self.assertEqual(second.value, expected_second_value.encode('utf-8'))

    def test_file_content_single(self):
        filenames = ('file.txt', 'image-600x400.png', 'image-2560x1600.png')

        for filename in filenames:
            with open_dataset(filename) as dataset_:
                expected_value = dataset_.read()

            content_type, body = encoded_dataset(filename)

            value = ValueTarget()

            parser = StreamingFormDataParser(
                headers={'Content-Type': content_type})
            parser.register(filename, value)

            parser.data_received(body)

            self.assertEqual(value.value, expected_value)

    def test_file_content_multiple(self):
        with open_dataset('file.txt') as dataset_:
            expected_value = dataset_.read()

        content_type, body = encoded_dataset('file.txt')

        txt = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': content_type})
        parser.register('file.txt', txt)

        size = 50
        chunks = []

        while body:
            chunks.append(body[:size])
            body = body[size:]

        for chunk in chunks:
            parser.data_received(chunk)

        self.assertEqual(txt.value, expected_value)

    def test_file_content_varying_chunk_size(self):
        with open_dataset('file.txt') as dataset_:
            expected_value = dataset_.read()

        content_type, body = encoded_dataset('file.txt')

        for index in range(len(body)):
            txt = ValueTarget()

            parser = StreamingFormDataParser(
                headers={'Content-Type': content_type})
            parser.register('file.txt', txt)

            parser.data_received(body[:index])
            parser.data_received(body[index:])

            self.assertEqual(txt.value, expected_value)

    def test_mixed_content_varying_chunk_size(self):
        with open_dataset('file.txt') as dataset_:
            expected_value = dataset_.read()

        with open_dataset('file.txt') as dataset_:
            fields = {
                'name': 'hello world',
                'age': '10',
                'cv.txt': ('file.txt', dataset_, 'text/plain')
            }

            encoder = MultipartEncoder(fields=fields)

            body = encoder.to_string()
            content_type = encoder.content_type

        for index in range(len(body)):
            name = ValueTarget()
            age = ValueTarget()
            cv = ValueTarget()

            parser = StreamingFormDataParser(
                headers={'Content-Type': content_type})

            parser.register('name', name)
            parser.register('age', age)
            parser.register('cv.txt', cv)

            parser.data_received(body[:index])
            parser.data_received(body[index:])

            self.assertEqual(name.value, b'hello world')
            self.assertEqual(age.value, b'10')
            self.assertEqual(cv.value, expected_value)

    def test_parameter_contains_crlf(self):
        target = ValueTarget()

        encoder = MultipartEncoder(fields={'value': 'hello\r\nworld'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)
        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello\r\nworld')

    def test_parameter_ends_with_crlf(self):
        target = ValueTarget()

        encoder = MultipartEncoder(fields={'value': 'hello\r\n'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)

        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'hello\r\n')

    def test_parameter_starts_with_crlf(self):
        target = ValueTarget()

        encoder = MultipartEncoder(fields={'value': '\r\nworld'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.register('value', target)

        parser.data_received(encoder.to_string())

        self.assertEqual(target.value, b'\r\nworld')

    def test_multiple_files(self):
        txt_filename = 'file.txt'
        png_filename = 'image-600x400.png'

        with open_dataset(txt_filename) as dataset_:
            expected_txt = dataset_.read()

        with open_dataset(png_filename) as dataset_:
            expected_png = dataset_.read()

        txt_target = ValueTarget()
        png_target = ValueTarget()

        with open_dataset(txt_filename) as txt_file, \
                open_dataset(png_filename) as png_file:
            encoder = MultipartEncoder(fields={
                txt_filename: (txt_filename, txt_file,
                               'application/plain'),
                png_filename: (png_filename, png_file, 'image/png')
            })

            parser = StreamingFormDataParser(
                headers={'Content-Type': encoder.content_type})

            parser.register(txt_filename, txt_target)
            parser.register(png_filename, png_target)

            parser.data_received(encoder.to_string())

            self.assertEqual(txt_target.value, expected_txt)
            self.assertEqual(png_target.value, expected_png)

    def test_large_file(self):
        for filename in ['image-500k.png', 'image-2560x1600.png',
                         'image-600x400.png', 'image-high-res.jpg']:
            with open_dataset(filename) as dataset_:
                expected_value = dataset_.read()

            content_type, body = encoded_dataset(filename)

            value = ValueTarget()

            parser = StreamingFormDataParser(
                headers={'Content-Type': content_type})
            parser.register(filename, value)

            parser.data_received(body)

            self.assertEqual(value.value, expected_value)

    # The following tests have been added from tornado's
    # MultipartFormDataTestCase
    # https://github.com/tornadoweb/tornado/blob/master/tornado/test/httputil_test.py

    def test_file_upload(self):
        data = b'''\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')
        self.assertEqual(target._started, True)
        self.assertEqual(target._finished, True)

    def test_unquoted_names(self):
        data = b'''\
--1234
Content-Disposition: form-data; name=files; filename=ab.txt

Foo
--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')

    def test_special_filenames(self):
        filenames = ['a;b.txt',
                     'a"b.txt',
                     'a";b.txt',
                     'a;"b.txt',
                     'a";";.txt',
                     'a\\"b.txt',
                     'a\\b.txt']

        for filename in filenames:
            data = '''\
--1234
Content-Disposition: form-data; name=files; filename={}

Foo
--1234--'''.format(filename).replace('\n', '\r\n').encode('utf-8')

            target = ValueTarget()

            parser = StreamingFormDataParser(
                headers={'Content-Type': 'multipart/form-data; boundary=1234'})
            parser.register('files', target)

            parser.data_received(data)

            self.assertEqual(target.value, b'Foo')

    def test_boundary_starts_and_ends_with_quotes(self):
        data = b'''\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary="1234"'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')

    def test_missing_headers(self):
        data = '''\
--1234

Foo
--1234--'''.replace('\n', '\r\n').encode('utf-8')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'')

    def test_invalid_content_disposition(self):
        data = b'''\
--1234
Content-Disposition: invalid; name="files"; filename="ab.txt"

Foo
--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'')

    def test_line_does_not_end_with_correct_linebreak(self):
        data = b'''\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')

    def test_without_name_parameter(self):
        data = b'''\
--1234
Content-Disposition: form-data; filename="ab.txt"

Foo
--1234--'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'')

    def test_data_after_final_boundary(self):
        data = b'''\
--1234
Content-Disposition: form-data; name="files"; filename="ab.txt"

Foo
--1234--
'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')

    def test_register_after_data_received(self):
        encoder = MultipartEncoder(fields={'name': 'hello'})

        parser = StreamingFormDataParser(
            headers={'Content-Type': encoder.content_type})
        parser.data_received(encoder.to_string())

        self.assertRaises(ParseFailedException, parser.register,
                          'name', ValueTarget())

    def test_missing_filename_directive(self):
        data = b'''\
--1234
Content-Disposition: form-data; name="files"

Foo
--1234--
'''.replace(b'\n', b'\r\n')

        target = ValueTarget()

        self.assertFalse(target.multipart_filename)

        parser = StreamingFormDataParser(
            headers={'Content-Type': 'multipart/form-data; boundary=1234'})
        parser.register('files', target)

        parser.data_received(data)

        self.assertEqual(target.value, b'Foo')
        self.assertFalse(target.multipart_filename)

    def test_filename_passed_to_target(self):
        filename = 'file.txt'

        content_type, body = encoded_dataset(filename)

        target = ValueTarget()

        self.assertFalse(target.multipart_filename)

        parser = StreamingFormDataParser(
            headers={'Content-Type': content_type})
        parser.register(filename, target)
        parser.data_received(body)

        self.assertEqual(target.multipart_filename, filename)
