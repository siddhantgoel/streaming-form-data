import cgi

from streaming_form_data.targets import NullTarget

ctypedef unsigned char Byte
ctypedef size_t Index

cdef enum Constants:
    Hyphen = 45
    CR = 13
    LF = 10
    MinFileBodyChunkSize = 1024


cdef enum FinderState:
    FS_START, FS_WORKING, FS_END


# Knuth-Morris-Pratt algorithm
cdef class Finder:
    cdef bytes target
    cdef const Byte *target_ptr
    cdef Index target_len, index
    cdef FinderState state

    def __init__(self, target):
        if len(target) < 1:
            raise ValueError('Empty values not allowed')

        self.target = target
        self.target_ptr = self.target
        self.target_len = len(self.target)
        self.index = 0
        self.state = FinderState.FS_START

    cpdef feed(self, Byte byte):
        if byte != self.target_ptr[self.index]:
            if self.state != FinderState.FS_START:
                self.state = FinderState.FS_START
                self.index = 0
                # try matching substring
                # This is not universal code, but the code specialized from multipart delimiters
                # (length is at least 5 bytes, starting with \r\n and has no \r\n in the middle)
                if byte == self.target_ptr[0]:
                    self.state = FinderState.FS_WORKING
                    self.index = 1
        else:
            self.state = FinderState.FS_WORKING
            self.index += 1

            if self.index == self.target_len:
                self.state = FinderState.FS_END

    cpdef reset(self):
        self.state = FinderState.FS_START
        self.index = 0

    @property
    def target(self):
        return self.target

    cpdef bint inactive(self):
        return self.state == FinderState.FS_START

    cpdef bint active(self):
        return self.state == FinderState.FS_WORKING

    cpdef bint found(self):
        return self.state == FinderState.FS_END

    cpdef Index matched_length(self):
        return self.index


class Part:
    """One part of a multipart/form-data request
    """

    def __init__(self, name, target):
        self.name = name
        self.target = target

        self._reading = False

    def set_multipart_filename(self, value):
        self.target.multipart_filename = value

    def start(self):
        self._reading = True
        self.target.start()
        self.target._started = True

    def data_received(self, chunk):
        self.target.data_received(chunk)

    def finish(self):
        self._reading = False
        self.target.finish()
        self.target._finished = True

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
    cdef ParserState state
    cdef Finder delimiter_finder, ender_finder
    cdef Index delimiter_length, ender_length
    cdef object expected_parts
    cdef object active_part, default_part

    cdef bytes _leftover_buffer

    def __init__(self, delimiter, ender):
        self.delimiter_finder = Finder(delimiter)
        self.ender_finder = Finder(ender)

        self.delimiter_length = len(delimiter)
        self.ender_length = len(ender)

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
        if self.active_part and len(value) > 0:
            self.active_part.data_received(value)

    cdef _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    cpdef int data_received(self, bytes data):
        if not data:
            return 0

        cdef bytes chunk
        cdef Index index

        if self._leftover_buffer:
            chunk = self._leftover_buffer + data
            index = len(self._leftover_buffer)
            self._leftover_buffer = None
        else:
            chunk = data
            index = 0

        return self._parse(chunk, index)

    cdef int _parse(self, bytes chunk, Index index):
        cdef Index idx, buffer_start, chunk_len
        cdef Index match_start, skip_count, matched_length
        cdef Byte byte
        cdef const Byte *chunk_ptr
        chunk_ptr = chunk
        chunk_len = len(chunk)
        buffer_start = 0

        idx = index
        while idx < chunk_len:
            byte = chunk_ptr[idx]

            if self.state == ParserState.PS_START:
                if byte != Constants.Hyphen:
                    return 10

                self.state = ParserState.PS_STARTING_BOUNDARY
            elif self.state == ParserState.PS_STARTING_BOUNDARY:
                if byte != Constants.Hyphen:
                    return 20

                self.state = ParserState.PS_READING_BOUNDARY
            elif self.state == ParserState.PS_READING_BOUNDARY:
                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_BOUNDARY

            elif self.state == ParserState.PS_ENDING_BOUNDARY:
                if byte != Constants.LF:
                    return 30
                if buffer_start != 0:
                    return 40
                # ensure we have read correct starting delimiter
                if b'\r\n' + chunk[buffer_start: idx + 1] != self.delimiter_finder.target:
                    return 50

                buffer_start = idx + 1

                self.state = ParserState.PS_READING_HEADER
            elif self.state == ParserState.PS_READING_HEADER:
                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_HEADER

            elif self.state == ParserState.PS_ENDING_HEADER:
                if byte != Constants.LF:
                    return 60

                value, params = cgi.parse_header(
                    chunk[buffer_start: idx + 1].decode('utf-8'))

                if value.startswith('Content-Disposition') and \
                        value.endswith('form-data'):
                    name = params.get('name')
                    if name:
                        part = self._part_for(name) or self.default_part

                        part.set_multipart_filename(params.get('filename'))
                        part.start()

                        self.set_active_part(part)

                buffer_start = idx + 1

                self.state = ParserState.PS_ENDED_HEADER
            elif self.state == ParserState.PS_ENDED_HEADER:
                if byte == Constants.CR:
                    self.state = ParserState.PS_ENDING_ALL_HEADERS
                else:
                    self.state = ParserState.PS_READING_HEADER

            elif self.state == ParserState.PS_ENDING_ALL_HEADERS:
                if byte != Constants.LF:
                    return 70

                buffer_start = idx + 1

                self.state = ParserState.PS_READING_BODY
            elif self.state == ParserState.PS_READING_BODY:

                self.delimiter_finder.feed(byte)
                self.ender_finder.feed(byte)

                if self.delimiter_finder.found():
                    self.state = ParserState.PS_READING_HEADER

                    if idx + 1 < self.delimiter_length:
                        return 80
                    match_start = idx + 1 - self.delimiter_length

                    if match_start >= buffer_start:
                        self.on_body(chunk[buffer_start: match_start])

                        buffer_start = idx + 1
                    else:
                        return 90

                    self.unset_active_part()
                    self.delimiter_finder.reset()

                elif self.ender_finder.found():
                    self.state = ParserState.PS_END

                    if idx + 1 < self.ender_length:
                        return 100
                    match_start = idx + 1 - self.ender_length

                    if match_start >= buffer_start:
                         self.on_body(chunk[buffer_start: match_start])
                    else:
                        return 110

                    buffer_start = idx + 1

                    self.unset_active_part()
                    self.ender_finder.reset()
            elif self.state == ParserState.PS_END:
                return 0
            else:
                return 120

            idx += 1

        if idx != chunk_len:
            return 140
        if buffer_start > chunk_len:
            return 150

        if self.state == ParserState.PS_READING_BODY:
            matched_length = max(self.delimiter_finder.matched_length(),
                                 self.ender_finder.matched_length())
            match_start = idx - matched_length
            if match_start >= buffer_start + Constants.MinFileBodyChunkSize:
                self.on_body(chunk[buffer_start: match_start])
                buffer_start = match_start

        if idx - buffer_start > 0:
            self._leftover_buffer = chunk[buffer_start: idx]

        return 0
