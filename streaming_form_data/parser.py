import cgi

from streaming_form_data._parser import _Parser


class ParseFailedException(Exception):
    pass


def parse_content_boundary(headers):
    content_type = None

    for key in headers:
        if key.lower() == 'content-type':
            content_type = headers.get(key)
            break

    if not content_type:
        raise ParseFailedException('Missing Content-Type header')

    value, params = cgi.parse_header(content_type)

    if not value or value.lower() != 'multipart/form-data':
        raise ParseFailedException('Content-Type is not multipart/form-data')

    boundary = params.get('boundary')
    if not boundary:
        raise ParseFailedException('Boundary not found')

    return boundary.encode('utf-8')


class StreamingFormDataParser:
    def __init__(self, headers):
        self.headers = headers

        raw_boundary = parse_content_boundary(headers)

        boundary = b'--' + raw_boundary
        delimiter = boundary + b'\r\n'
        ender = boundary + b'--'

        self._parser = _Parser(delimiter, ender)

        self._running = False

    def register(self, name, target):
        if self._running:
            raise ParseFailedException(
                'Registering parts not allowed when parser is running')

        self._parser.register(name, target)

    def data_received(self, data):
        if not self._running:
            self._running = True

        if self._parser.data_received(data) > 0:
            raise ParseFailedException()
