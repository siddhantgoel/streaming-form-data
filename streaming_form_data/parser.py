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
    ENDING_BODY_CR = 8
    ENDING_BODY_LF = 9

    END = 10


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

        self.state = ParserState.START
        self._active_part = None

        self._default_part = Part('_default', NullTarget())

        self._buffer = []

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
            ParserState.ENDING_BODY_CR: self._parse_ending_body_cr,
            ParserState.ENDING_BODY_LF: self._parse_ending_body_lf,
        }.get

        for index in range(len(chunk)):
            function = next_step(self.state)

            if not function:
                raise ParseFailedException()

            function(index, chunk)

    def _parse_start(self, index, chunk):
        """Called when we see the first byte of the delimiter containing the
        boundary
        """
        byte = chunk[index]

        if byte != self._hyphen:
            raise ParseFailedException()

        self._buffer.append(byte)
        self.state = ParserState.STARTING_BOUNDARY

    def _parse_starting_boundary(self, index, chunk):
        """Called when we see the second byte of the delimiter containing the
        boundary
        """
        byte = chunk[index]

        if byte != self._hyphen:
            raise ParseFailedException()

        self._buffer.append(byte)
        self.state = ParserState.READING_BOUNDARY

    def _parse_reading_boundary(self, index, chunk):
        """Called on reading the carriage return in the boundary ending
        """
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_BOUNDARY

        self._buffer.append(byte)

    def _parse_ending_boundary(self, index, chunk):
        """Called on reading the linefeed in the boundary ending
        """
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._buffer.append(byte)
        self._process_boundary()
        self._reset_buffer()

        self.state = ParserState.READING_HEADER

    def _parse_reading_header(self, index, chunk):
        """Called on reading the first byte of a header line
        """
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_HEADER
        self._buffer.append(byte)

    def _parse_ending_header(self, index, chunk):
        """Called on reading the linefeed in the header ending
        """
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._buffer.append(byte)
        self._process_header()
        self._reset_buffer()

        self.state = ParserState.ENDED_HEADER

    def _parse_ended_header(self, index, chunk):
        """Called after the linefeed has been read in the previous header and
        we're not sure yet if there's another header or there's a \r\n and then
        the body is about to start.
        """
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_ALL_HEADERS
        else:
            self.state = ParserState.READING_HEADER

        self._buffer.append(byte)

    def _parse_ending_all_headers(self, index, chunk):
        """Called after all the headers have been read and the actual body is
        about to start.
        """
        byte = chunk[index]

        if byte != self._lf:
            raise ParseFailedException()

        self._reset_buffer()
        self.state = ParserState.READING_BODY

    def _parse_reading_body(self, index, chunk):
        """Called when the body is being read
        """
        byte = chunk[index]

        if byte == self._cr:
            self.state = ParserState.ENDING_BODY_CR
        self._buffer.append(byte)

    def _parse_ending_body_cr(self, index, chunk):
        byte = chunk[index]

        if byte == self._lf:
            self.state = ParserState.ENDING_BODY_LF

        self._buffer.append(byte)

    def _parse_ending_body_lf(self, index, chunk):
        byte = chunk[index]

        if byte == self._hyphen:
            self.state = ParserState.STARTING_BOUNDARY
            self._buffer.pop(-1)
            self._buffer.pop(-1)
        else:
            self.state = ParserState.READING_BODY
            self._buffer.append(byte)

        self._flush_buffer()

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

    def _flush_buffer(self):
        value = bytes(self._buffer)

        self._active_part.data_received(value)
        self._buffer = []
