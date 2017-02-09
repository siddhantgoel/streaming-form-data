import cgi


crlf = b'\r\n'


class ParseFailedException(Exception):
    pass


def parse_content_boundary(headers):
    content_type = headers.get('Content-Type')
    if not content_type:
        raise ParseFailedException()

    value, params = cgi.parse_header(content_type)

    if not value or value.lower() != 'multipart/form-data':
        raise ParseFailedException()

    boundary = params.get('boundary')
    if not boundary:
        raise ParseFailedException()

    return boundary


class StreamingFormDataParser(object):
    def __init__(self, parts, request):
        self.parts = parts
        self.request = request

        self._boundary = parse_content_boundary(request.headers)
        self._delimiter = b'--' + self._boundary + crlf
        self._ender = b'--' + self._boundary + b'--' + crlf

    def data_received(self, chunk):
        self._parse(chunk)

    def _parse(chunk):
        raise NotImplementedError()
