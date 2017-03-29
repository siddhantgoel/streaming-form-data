from collections import namedtuple
import cgi
import enum

from streaming_form_data.finder import Finder
from streaming_form_data.targets import NullTarget
from streaming_form_data.part import Part


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


Position = namedtuple('Position', ['buffer_start', 'buffer_end'])


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

    def data_received(self, data):
        if not self.expected_parts or not data:
            return

        if self._leftover_buffer:
            chunk = self._leftover_buffer + data

            index = len(self._leftover_buffer)
            buffer_start = 0
            buffer_end = index

            self._leftover_buffer = None
        else:
            chunk = data

            index = 0
            buffer_start = 0
            buffer_end = 0

        self._parse(chunk, index, buffer_start, buffer_end)

    def _parse(self, chunk, index, buffer_start, buffer_end):
        position = Position(buffer_start, buffer_end)

        def expand_buffer():
            return position._replace(buffer_end=position.buffer_end+1)

        def buffer_length():
            return position.buffer_end - position.buffer_start

        def reset_buffer():
            return position._replace(buffer_start=index+1,
                                     buffer_end=index+1)

        def truncate_buffer(suffix):
            if buffer_length() <= len(suffix):
                return position

            idx = position.buffer_end - len(suffix)

            self._active_part.data_received(
                chunk[position.buffer_start: idx - 2])

            return reset_buffer()

        def try_flush_buffer():
            if buffer_length() <= self._max_buffer_size:
                return position

            index = position.buffer_end - 1

            self._active_part.data_received(
                chunk[position.buffer_start: index])

            return position._replace(buffer_start=index)

        while index < len(chunk):
            byte = chunk[index]

            if self.state == ParserState.START:
                if byte != HYPHEN:
                    raise ParseFailedException()

                position = expand_buffer()
                self.state = ParserState.STARTING_BOUNDARY
            elif self.state == ParserState.STARTING_BOUNDARY:
                if byte != HYPHEN:
                    raise ParseFailedException()

                position = expand_buffer()
                self.state = ParserState.READING_BOUNDARY
            elif self.state == ParserState.READING_BOUNDARY:
                position = expand_buffer()

                if byte == CR:
                    self.state = ParserState.ENDING_BOUNDARY
            elif self.state == ParserState.ENDING_BOUNDARY:
                if byte != LF:
                    raise ParseFailedException()

                position = expand_buffer()

                if buffer_length() < 4:
                    return False

                indices = (position.buffer_start,
                           position.buffer_start + 1,
                           position.buffer_end - 1,
                           position.buffer_end - 2)

                if all([chunk[idx] == HYPHEN for idx in indices]):
                    self.state = ParserState.END

                position = reset_buffer()

                self.state = ParserState.READING_HEADER
            elif self.state == ParserState.READING_HEADER:
                position = expand_buffer()

                if byte == CR:
                    self.state = ParserState.ENDING_HEADER
            elif self.state == ParserState.ENDING_HEADER:
                if byte != LF:
                    raise ParseFailedException()

                position = expand_buffer()

                header = chunk[position.buffer_start: position.buffer_end]

                value, params = cgi.parse_header(header.decode('utf-8'))

                if value.startswith('Content-Disposition'):
                    part = self._part_for(params['name'])
                    part.start()

                    self._set_active_part(part)

                position = reset_buffer()

                self.state = ParserState.ENDED_HEADER
            elif self.state == ParserState.ENDED_HEADER:
                if byte == CR:
                    self.state = ParserState.ENDING_ALL_HEADERS
                else:
                    self.state = ParserState.READING_HEADER

                position = expand_buffer()
            elif self.state == ParserState.ENDING_ALL_HEADERS:
                if byte != LF:
                    raise ParseFailedException()

                position = reset_buffer()
                self.state = ParserState.READING_BODY
            elif self.state == ParserState.READING_BODY:
                position = expand_buffer()

                self._delimiter_finder.feed(byte)
                self._ender_finder.feed(byte)

                if self._delimiter_finder.found:
                    self.state = ParserState.READING_HEADER
                    position = truncate_buffer(self._delimiter)
                    self._unset_active_part()
                    self._delimiter_finder.reset()
                elif self._ender_finder.found:
                    self.state = ParserState.END
                    position = truncate_buffer(self._ender)
                    self._ender_finder.reset()
                else:
                    if self._ender_finder.inactive and \
                            self._delimiter_finder.inactive:
                        position = try_flush_buffer()
            elif self.state == ParserState.END:
                return
            else:
                raise ParseFailedException()

            index += 1

        if buffer_length() > 0:
            self._leftover_buffer = \
                chunk[position.buffer_start: position.buffer_end]

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
