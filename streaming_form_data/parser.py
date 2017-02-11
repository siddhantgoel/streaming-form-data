import cgi
import enum

from streaming_form_data.targets import NullTarget
from streaming_form_data.part import Part


class ParseFailedException(Exception):
    pass


class ParserState(enum.Enum):
    START = -1

    STARTING_BOUNDARY = 0
    READING_BOUNDARY = 1
    ENDING_BOUNDARY = 2

    READING_HEADER = 3
    ENDING_HEADER = 4
    ENDED_HEADER = 5

    ENDING_ALL_HEADERS = 6

    READING_BODY = 7

    END = 8


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


class StreamingFormDataParser(object):
    """Parse multipart/form-data in chunks, one at a time.
    """

    def __init__(self, expected_parts, headers):
        self.expected_parts = expected_parts
        self.headers = headers

        self._hyphen = 45
        self._cr = 13
        self._lf = 10

        self._raw_boundary = parse_content_boundary(headers)

        self._boundary = b'--' + self._raw_boundary
        self._delimiter = self._boundary + b'\r\n'
        self._ender = self._boundary + b'--\r\n'

        self.state = ParserState.START
        self._active_part = None

        self._default_part = Part('_default', NullTarget())

        self._buffer = []
        self._max_buffer_size = len(self._delimiter) + 32

    def _unset_active_part(self):
        if self._active_part:
            self._active_part.finish()
        self._active_part = None

    def _set_active_part(self, part):
        self._unset_active_part()
        self._active_part = part

    def data_received(self, chunk):
        if not self.expected_parts or not chunk:
            return

        self._parse(chunk)

    def _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part
        return self._default_part

    def _parse(self, chunk):
        next_step = {
            ParserState.START: self._parse_start,
            ParserState.STARTING_BOUNDARY: self._parse_starting_boundary,
            ParserState.READING_BOUNDARY: self._parse_reading_boundary,
            ParserState.ENDING_BOUNDARY: self._parse_ending_boundary,
            ParserState.READING_HEADER: self._parse_reading_header,
            ParserState.ENDING_HEADER: self._parse_ending_header,
            ParserState.ENDED_HEADER: self._parse_ended_header,
            ParserState.ENDING_ALL_HEADERS: self._parse_ending_all_headers,
            ParserState.READING_BODY: self._parse_reading_body,
        }.get

        for index in range(len(chunk)):
            if self.state == ParserState.END:
                return

            function = next_step(self.state)

            if not function:
                raise ParseFailedException()

            function(index, chunk)

    def _parse_start(self, index, chunk):
        byte = chunk[index]

        if byte != self._hyphen:
            raise ParseFailedException()

        self._buffer.append(byte)
        self.state = ParserState.STARTING_BOUNDARY

    def _parse_starting_boundary(self, index, chunk):
        byte = chunk[index]

        if byte != self._hyphen:
            raise ParseFailedException()

        self._buffer.append(byte)
        self.state = ParserState.READING_BOUNDARY

    def _parse_reading_boundary(self, index, chunk):
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_BOUNDARY

        self._buffer.append(byte)

    def _parse_ending_boundary(self, index, chunk):
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._buffer.append(byte)
        self._process_boundary()
        self._reset_buffer()

        self.state = ParserState.READING_HEADER

    def _parse_reading_header(self, index, chunk):
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_HEADER

        self._buffer.append(byte)

    def _parse_ending_header(self, index, chunk):
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._buffer.append(byte)
        self._process_header()
        self._reset_buffer()

        self.state = ParserState.ENDED_HEADER

    def _parse_ended_header(self, index, chunk):
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_ALL_HEADERS
        else:
            self.state = ParserState.READING_HEADER

        self._buffer.append(byte)

    def _parse_ending_all_headers(self, index, chunk):
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._reset_buffer()
        self.state = ParserState.READING_BODY

    def _parse_reading_body(self, index, chunk):
        self._buffer.append(chunk[index])

        if self._buffer_ends_with(self._delimiter):
            self.state = ParserState.READING_HEADER
            self._truncate_buffer(self._delimiter)
            self._unset_active_part()
        elif self._buffer_ends_with(self._ender):
            self.state = ParserState.END
            self._truncate_buffer(self._ender)

        self._try_flush_buffer()

    def _process_header(self):
        header = bytes(self._buffer)

        value, params = cgi.parse_header(header.decode('utf-8'))

        if value.startswith('Content-Disposition'):
            part = self._part_for(params['name'])
            part.start()

            self._set_active_part(part)

    def _process_boundary(self):
        value = bytes(self._buffer)

        if all([value[index] == self._hyphen for index in (0, 1, -1, -2)]):
            self.state = ParserState.END

    def _reset_buffer(self):
        self._buffer = []

    def _try_flush_buffer(self):
        if len(self._buffer) <= self._max_buffer_size:
            return

        index = len(self._buffer) - self._max_buffer_size - 1

        self._active_part.data_received(self._buffer[:index])
        self._buffer = self._buffer[index:]

    def _flush_buffer(self):
        value = bytes(self._buffer)

        self._active_part.data_received(value)
        self._buffer = []

    def _truncate_buffer(self, suffix):
        if len(self._buffer) <= len(suffix):
            return

        index = len(self._buffer) - len(suffix)

        self._active_part.data_received(self._buffer[:index - 2])
        self._buffer = []

    def _buffer_ends_with(self, suffix):
        if len(self._buffer) < len(suffix):
            return False

        start = -1
        end = -1 * len(suffix)

        while start >= end:
            if self._buffer[start] != suffix[start]:
                return False
            start -= 1

        return True
