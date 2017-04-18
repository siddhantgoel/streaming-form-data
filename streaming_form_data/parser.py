import cgi

from streaming_form_data._parser import _Parser, _Failed
from streaming_form_data.targets import NullTarget


class ParseFailedException(Exception):
    pass


def parse_content_boundary(headers):
    content_type = headers.get('Content-Type')
    if not content_type:
        raise ParseFailedException()

    value, params = cgi.parse_header(content_type)

    if not value or value.lower() != 'multipart/form-data':
        raise ParseFailedException('Content-Type not multipart/form-data')

    boundary = params.get('boundary')
    if not boundary:
        raise ParseFailedException('Boundary not found')

    return boundary.encode('utf-8')


class Context(object):
    def __init__(self):
        self._part = None

    def set_active_part(self, part):
        self._part = part

    def unset_active_part(self):
        if self._part:
            self._part.finish()
        self.set_active_part(None)

    def get_active_part(self):
        return self._part


class Part(object):
    """One part of a multipart/form-data request
    """

    def __init__(self, name, target):
        self.name = name
        self.target = target

        self._reading = False

    def start(self):
        self._reading = True
        self.target.start()

    def data_received(self, chunk):
        self.target.data_received(chunk)

    def finish(self):
        self._reading = False
        self.target.finish()

    @property
    def is_reading(self):
        return self._reading


class StreamingFormDataParser(object):
    def __init__(self, headers):
        self.expected_parts = []
        self.headers = headers

        raw_boundary = parse_content_boundary(headers)

        boundary = b'--' + raw_boundary
        delimiter = boundary + b'\r\n'
        ender = boundary + b'--'

        context = Context()

        def on_header(header):
            value, params = cgi.parse_header(header.decode('utf-8'))

            if not value.startswith('Content-Disposition') or \
                    not value.endswith('form-data'):
                return

            name = params.get('name')
            if not name:
                return

            part = self._part_for(name) or Part('_default', NullTarget())
            part.start()

            context.set_active_part(part)

        def on_body(value):
            part = context.get_active_part()
            if not part:
                return

            part.data_received(value)

        def unset_active_part():
            context.unset_active_part()

        self._parser = _Parser(delimiter, ender,
                               on_header, on_body, unset_active_part)

        self._running = False

    def register(self, name, target):
        if self._running:
            raise ParseFailedException(
                'Registering parts not allowed when parser is running')

        part = self._part_for(name)

        if not part:
            self.expected_parts.append(Part(name, target))

    def _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    def data_received(self, data):
        if not self._running:
            self._running = True

        try:
            self._parser.data_received(data)
        except _Failed:
            raise ParseFailedException()
