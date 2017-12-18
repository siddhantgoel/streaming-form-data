import cgi

from streaming_form_data.targets import NullTarget


cdef enum Constants:
    Hyphen = 45
    CR = 13
    LF = 10
    MaxBufferSize = 1024


cdef enum FinderState:
    FS_START, FS_WORKING, FS_END


cdef class Finder:
    cdef bytes target
    cdef long index
    cdef FinderState state

    def __init__(self, target):
        if len(target) < 1:
            raise ValueError('Empty values not allowed')

        self.target = target
        self.index = 0
        self.state = FinderState.FS_START

    cpdef feed(self, long byte):
        if byte != self.target[self.index]:
            self.state = FinderState.FS_START
            self.index = 0
        else:
            self.state = FinderState.FS_WORKING
            self.index += 1

            if self.index == len(self.target):
                self.state = FinderState.FS_END

    cpdef reset(self):
        self.state = FinderState.FS_START
        self.index = 0

    @property
    def target(self):
        return self.target

    @property
    def inactive(self):
        return self.state == FinderState.FS_START

    @property
    def active(self):
        return self.state == FinderState.FS_WORKING

    @property
    def found(self):
        return self.state == FinderState.FS_END


class _Failed(Exception):
    pass


class Part:
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


cdef enum ParserState:
    PS_START,

    PS_STARTING_BOUNDARY, PS_READING_BOUNDARY, PS_ENDING_BOUNDARY,

    PS_READING_HEADER, PS_ENDING_HEADER, PS_ENDED_HEADER, PS_ENDING_ALL_HEADERS,

    PS_READING_BODY,

    PS_END


cdef class _Parser:
    cdef bytes delimiter, ender
    cdef ParserState state
    cdef Finder delimiter_finder, ender_finder
    cdef object expected_parts
    cdef object active_part, default_part

    cdef bytes _leftover_buffer

    def __init__(self, delimiter, ender):
        self.delimiter = delimiter
        self.ender = ender

        self.delimiter_finder = Finder(delimiter)
        self.ender_finder = Finder(ender)

        self.state = ParserState.PS_START

        self.expected_parts = []

        self.active_part = None
        self.default_part = Part('_default', NullTarget())

        self._leftover_buffer = None

    cpdef register(self, str name, object target):
        if not self._part_for(name):
            self.expected_parts.append(Part(name, target))

    cdef set_active_part(self, part):
        self.active_part = part

    cdef unset_active_part(self):
        if self.active_part:
            self.active_part.finish()
        self.set_active_part(None)

    cdef on_body(self, bytes value):
        if self.active_part:
            self.active_part.data_received(value)

    cdef _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    cpdef data_received(self, bytes data):
        if not data:
            return

        cdef bytes chunk
        cdef long index, buffer_start, buffer_end

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

    cdef _parse(self, bytes chunk, long index,
                long buffer_start, long buffer_end):
        while index < len(chunk):
            byte = chunk[index]

            if self.state == ParserState.PS_START:
                if byte != Constants.Hyphen:
                    raise _Failed()

                buffer_end += 1
                self.state = ParserState.PS_STARTING_BOUNDARY
            elif self.state == ParserState.PS_STARTING_BOUNDARY:
                if byte != Constants.Hyphen:
                    raise _Failed()

                buffer_end += 1
                self.state = ParserState.PS_READING_BOUNDARY
            elif self.state == ParserState.PS_READING_BOUNDARY:
                buffer_end += 1

                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_BOUNDARY
            elif self.state == ParserState.PS_ENDING_BOUNDARY:
                if byte != Constants.LF:
                    raise _Failed()

                buffer_end += 1

                if buffer_end - buffer_start < 4:
                    return False

                indices = (buffer_start,
                           buffer_start + 1,
                           buffer_end - 1,
                           buffer_end - 2)

                if all([chunk[idx] == Constants.Hyphen for idx in indices]):
                    self.state = ParserState.PS_END

                buffer_start = buffer_end = index + 1

                self.state = ParserState.PS_READING_HEADER
            elif self.state == ParserState.PS_READING_HEADER:
                buffer_end += 1

                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_HEADER
            elif self.state == ParserState.PS_ENDING_HEADER:
                if byte != Constants.LF:
                    raise _Failed()

                buffer_end += 1

                value, params = cgi.parse_header(
                    chunk[buffer_start: buffer_end].decode('utf-8'))

                if value.startswith('Content-Disposition') and \
                        value.endswith('form-data'):
                    name = params.get('name')
                    if name:
                        part = self._part_for(name) or self.default_part
                        part.start()

                        self.set_active_part(part)

                buffer_start = buffer_end = index + 1

                self.state = ParserState.PS_ENDED_HEADER
            elif self.state == ParserState.PS_ENDED_HEADER:
                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_ALL_HEADERS
                else:
                    self.state = ParserState.PS_READING_HEADER

                buffer_end += 1
            elif self.state == ParserState.PS_ENDING_ALL_HEADERS:
                if byte != Constants.LF:
                    raise _Failed()

                buffer_start = buffer_end = index + 1
                self.state = ParserState.PS_READING_BODY
            elif self.state == ParserState.PS_READING_BODY:
                buffer_end += 1

                self.delimiter_finder.feed(byte)
                self.ender_finder.feed(byte)

                if self.delimiter_finder.found:
                    self.state = ParserState.PS_READING_HEADER

                    if buffer_end - buffer_start > len(self.delimiter):
                        idx = buffer_end - len(self.delimiter)

                        self.on_body(chunk[buffer_start: idx - 2])

                        buffer_start = buffer_end = index + 1

                    self.unset_active_part()
                    self.delimiter_finder.reset()
                elif self.ender_finder.found:
                    self.state = ParserState.PS_END

                    if buffer_end - buffer_start > len(self.ender):
                        idx = buffer_end - len(self.ender)

                        if chunk[idx - 1] == Constants.LF and \
                                chunk[idx - 2] == Constants.CR:
                            self.on_body(chunk[buffer_start: idx - 2])
                        else:
                            self.on_body(chunk[buffer_start: idx])

                        buffer_start = buffer_end = index + 1

                    self.unset_active_part()
                    self.ender_finder.reset()
                else:
                    if self.ender_finder.inactive and \
                            self.delimiter_finder.inactive and \
                            buffer_end - buffer_start > Constants.MaxBufferSize:
                        idx = buffer_end - 1

                        self.on_body(chunk[buffer_start: idx])

                        buffer_start = index
            elif self.state == ParserState.PS_END:
                return
            else:
                raise _Failed()

            index += 1

        if buffer_end - buffer_start > 0:
            self._leftover_buffer = chunk[buffer_start: buffer_end]
