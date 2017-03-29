import cgi
import enum

from streaming_form_data.finder import Finder
from streaming_form_data.targets import NullTarget
from streaming_form_data.part import Part


HYPHEN = 45

CR = 13

LF = 10

MAX_BUFFER_SIZE = 1024


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
        def buffer_length():
            return buffer_end - buffer_start

        while index < len(chunk):
            byte = chunk[index]

            if self.state == ParserState.START:
                if byte != HYPHEN:
                    raise ParseFailedException()

                buffer_end += 1
                self.state = ParserState.STARTING_BOUNDARY
            elif self.state == ParserState.STARTING_BOUNDARY:
                if byte != HYPHEN:
                    raise ParseFailedException()

                buffer_end += 1
                self.state = ParserState.READING_BOUNDARY
            elif self.state == ParserState.READING_BOUNDARY:
                buffer_end += 1

                if byte == CR:
                    self.state = ParserState.ENDING_BOUNDARY
            elif self.state == ParserState.ENDING_BOUNDARY:
                if byte != LF:
                    raise ParseFailedException()

                buffer_end += 1

                if buffer_length() < 4:
                    return False

                indices = (buffer_start,
                           buffer_start + 1,
                           buffer_end - 1,
                           buffer_end - 2)

                if all([chunk[idx] == HYPHEN for idx in indices]):
                    self.state = ParserState.END

                buffer_start = buffer_end = index + 1

                self.state = ParserState.READING_HEADER
            elif self.state == ParserState.READING_HEADER:
                buffer_end += 1

                if byte == CR:
                    self.state = ParserState.ENDING_HEADER
            elif self.state == ParserState.ENDING_HEADER:
                if byte != LF:
                    raise ParseFailedException()

                buffer_end += 1

                header = chunk[buffer_start: buffer_end]

                value, params = cgi.parse_header(header.decode('utf-8'))

                if value.startswith('Content-Disposition'):
                    part = self._part_for(params['name'])
                    part.start()

                    self._set_active_part(part)

                buffer_start = buffer_end = index + 1

                self.state = ParserState.ENDED_HEADER
            elif self.state == ParserState.ENDED_HEADER:
                if byte == CR:
                    self.state = ParserState.ENDING_ALL_HEADERS
                else:
                    self.state = ParserState.READING_HEADER

                buffer_end += 1
            elif self.state == ParserState.ENDING_ALL_HEADERS:
                if byte != LF:
                    raise ParseFailedException()

                buffer_start = buffer_end = index + 1
                self.state = ParserState.READING_BODY
            elif self.state == ParserState.READING_BODY:
                buffer_end += 1

                self._delimiter_finder.feed(byte)
                self._ender_finder.feed(byte)

                if self._delimiter_finder.found:
                    self.state = ParserState.READING_HEADER

                    if buffer_length() > len(self._delimiter):
                        idx = buffer_end - len(self._delimiter)

                        self._active_part.data_received(
                            chunk[buffer_start: idx - 2])

                        buffer_start = buffer_end = index + 1

                    self._unset_active_part()
                    self._delimiter_finder.reset()
                elif self._ender_finder.found:
                    self.state = ParserState.END

                    if buffer_length() > len(self._ender):
                        idx = buffer_end - len(self._ender)

                        self._active_part.data_received(
                            chunk[buffer_start: idx - 2])

                        buffer_start = buffer_end = index + 1

                    self._ender_finder.reset()
                else:
                    if self._ender_finder.inactive and \
                            self._delimiter_finder.inactive and \
                            buffer_length() > MAX_BUFFER_SIZE:
                        idx = buffer_end - 1

                        self._active_part.data_received(
                            chunk[buffer_start: idx])

                        buffer_start = index
            elif self.state == ParserState.END:
                return
            else:
                raise ParseFailedException()

            index += 1

        if buffer_length() > 0:
            self._leftover_buffer = chunk[buffer_start: buffer_end]

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
