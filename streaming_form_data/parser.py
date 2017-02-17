import cgi
import enum

from .finder import Finder
from .targets import NullTarget
from .part import Part


HYPHEN = 45

CR = 13

LF = 10


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
    """Parse multipart/form-data in chunks, one byte at a time.
    """

    def __init__(self, expected_parts, headers):
        self.expected_parts = expected_parts
        self.headers = headers

        self._raw_boundary = parse_content_boundary(headers)

        self._boundary = b'--' + self._raw_boundary
        self._delimiter = self._boundary + b'\r\n'
        self._ender = self._boundary + b'--\r\n'

        self.state = ParserState.START
        self._active_part = None

        self._default_part = Part('_default', NullTarget())

        # current chunk we're parsing
        self._chunk = None

        # stores the index of the byte we're currently looking at
        self._index = -1

        # stores the indices where the current buffer starts (inclusive) and
        # ends (exclusive)
        self._buffer_start = -1
        self._buffer_end = -1

        self._max_buffer_size = 1024

        self._leftover_buffer = None

        self._delimiter_finder = Finder(self._delimiter)
        self._ender_finder = Finder(self._ender)

    @property
    def buffer_length(self):
        return self._buffer_end - self._buffer_start

    @property
    def _buffer(self):
        return self._chunk[self._buffer_start: self._buffer_end]

    def data_received(self, chunk):
        if not self.expected_parts or not chunk:
            return

        self._parse(chunk)

    def _parse(self, chunk):
        if self._leftover_buffer:
            self._chunk = self._leftover_buffer + chunk

            self._index = len(self._leftover_buffer)
            self._buffer_start = 0
            self._buffer_end = self._index

            self._leftover_buffer = None
        else:
            self._chunk = chunk

            self._index = 0
            self._buffer_start = 0
            self._buffer_end = 0

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

        while self._index < len(self._chunk):
            if self.state == ParserState.END:
                return

            function = next_step(self.state)

            if not function:
                raise ParseFailedException()

            function(self._chunk[self._index])

            self._index += 1

        if self.buffer_length > 0:
            self._leftover_buffer = \
                self._chunk[self._buffer_start: self._buffer_end]

        self._chunk = None

    def expand_buffer(self):
        self._buffer_end += 1

    def _parse_start(self, byte):
        if byte != HYPHEN:
            raise ParseFailedException()

        self.expand_buffer()
        self.state = ParserState.STARTING_BOUNDARY

    def _parse_starting_boundary(self, byte):
        if byte != HYPHEN:
            raise ParseFailedException()

        self.expand_buffer()
        self.state = ParserState.READING_BOUNDARY

    def _parse_reading_boundary(self, byte):
        self.expand_buffer()

        if byte == CR:
            self.state = ParserState.ENDING_BOUNDARY

    def _parse_ending_boundary(self, byte):
        if byte != LF:
            raise ParseFailedException()

        self.expand_buffer()
        self._process_boundary()
        self._reset_buffer()

        self.state = ParserState.READING_HEADER

    def _parse_reading_header(self, byte):
        self.expand_buffer()

        if byte == CR:
            self.state = ParserState.ENDING_HEADER

    def _parse_ending_header(self, byte):
        if byte != LF:
            raise ParseFailedException()

        self.expand_buffer()
        self._process_header()
        self._reset_buffer()

        self.state = ParserState.ENDED_HEADER

    def _parse_ended_header(self, byte):
        if byte == CR:
            self.state = ParserState.ENDING_ALL_HEADERS
        else:
            self.state = ParserState.READING_HEADER

        self.expand_buffer()

    def _parse_ending_all_headers(self, byte):
        if byte != LF:
            raise ParseFailedException()

        self._reset_buffer()
        self.state = ParserState.READING_BODY

    def _parse_reading_body(self, byte):
        self.expand_buffer()

        self._delimiter_finder.feed(byte)
        self._ender_finder.feed(byte)

        if self._delimiter_finder.found:
            self.state = ParserState.READING_HEADER
            self._truncate_buffer(self._delimiter)
            self._unset_active_part()
            self._delimiter_finder.reset()
        elif self._ender_finder.found:
            self.state = ParserState.END
            self._truncate_buffer(self._ender)
            self._ender_finder.reset()
        else:
            if self._ender_finder.inactive and self._delimiter_finder.inactive:
                self._try_flush_buffer()

    def _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part
        return self._default_part

    def _set_active_part(self, part):
        self._unset_active_part()
        self._active_part = part

    def _unset_active_part(self):
        if self._active_part:
            self._active_part.finish()
        self._active_part = None

    def _process_header(self):
        header = self._chunk[self._buffer_start: self._buffer_end]

        value, params = cgi.parse_header(header.decode('utf-8'))

        if value.startswith('Content-Disposition'):
            part = self._part_for(params['name'])
            part.start()

            self._set_active_part(part)

    def _process_boundary(self):
        if self.buffer_length < 4:
            return False

        indices = (self._buffer_start, self._buffer_start + 1,
                   self._buffer_end - 1, self._buffer_end - 2)

        if all([self._chunk[index] == HYPHEN for index in indices]):
            self.state = ParserState.END

    def _reset_buffer(self):
        self._buffer_start = self._index + 1
        self._buffer_end = self._index + 1

    def _try_flush_buffer(self):
        if self.buffer_length <= self._max_buffer_size:
            return

        index = self._buffer_end - 1

        self._active_part.data_received(
            self._chunk[self._buffer_start: index])

        self._buffer_start = index

    def _truncate_buffer(self, suffix):
        if self.buffer_length <= len(suffix):
            return

        index = self._buffer_end - len(suffix)

        self._active_part.data_received(
            self._chunk[self._buffer_start: index - 2])

        self._reset_buffer()
