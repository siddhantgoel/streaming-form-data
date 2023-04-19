# cython: language_level=3

from email.policy import HTTP
from email.parser import Parser

from streaming_form_data.targets import NullTarget


ctypedef unsigned char Byte  # noqa: E999


# useful constants

cdef int c_hyphen = 45
cdef int c_cr = 13
cdef int c_lf = 10
cdef int c_min_file_body_chunk_size = 1024


cdef enum FinderState:
    FS_START, FS_WORKING, FS_END


# 100..199: internal program errors (asserts)
# 200..299: problems with delimiting multipart stream into parts
# 300..399: problems with parsing particular part headers
cpdef enum ErrorGroup:
    Internal = 100
    Delimiting = 200
    PartHeaders = 300


cdef class Finder:
    cdef bytes target
    cdef const Byte *target_ptr
    cdef size_t target_len, index
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

                # Try matching substring
                # This is not universal, but specialized from multipart
                # delimiters (length at least 5 bytes, starting with \r\n and
                # has no \r\n in the middle)
                if byte == self.target_ptr[0]:
                    self.state = FinderState.FS_WORKING
                    self.index = 1
        else:
            self.state = FinderState.FS_WORKING
            self.index += 1

            if self.index == self.target_len:
                self.state = FinderState.FS_END

    cdef reset(self):
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

    cdef size_t matched_length(self):
        return self.index


cdef class Part:
    """One part of a multipart/form-data request
    """

    cdef public str name
    cdef list targets

    def __init__(self, str name, object target):
        self.name = name
        self.targets = [target]

    def add_target(self, object target):
        self.targets.append(target)

    def set_multipart_filename(self, str value):
        for target in self.targets:
            target.multipart_filename = value

    def set_multipart_content_type(self, str value):
        for target in self.targets:
            target.multipart_content_type = value

    def start(self):
        for target in self.targets:
            target.start()

    def data_received(self, bytes chunk):
        for target in self.targets:
            target.data_received(chunk)

    def finish(self):
        for target in self.targets:
            target.finish()


cdef enum ParserState:
    PS_START,
    PS_START_CR,

    PS_STARTING_BOUNDARY,
    PS_READING_BOUNDARY,
    PS_ENDING_BOUNDARY,

    PS_READING_HEADER,
    PS_ENDING_HEADER,
    PS_ENDED_HEADER,
    PS_ENDING_ALL_HEADERS,

    PS_READING_BODY,

    PS_END,

    PS_ERROR


cdef class _Parser:
    cdef ParserState state

    cdef Finder delimiter_finder, ender_finder
    cdef size_t delimiter_length, ender_length

    cdef object expected_parts
    cdef object active_part, default_part

    cdef bytes _leftover_buffer

    def __init__(self, bytes delimiter, bytes ender):
        self.delimiter_finder = Finder(delimiter)
        self.ender_finder = Finder(ender)

        self.delimiter_length = len(delimiter)
        self.ender_length = len(ender)

        self.state = ParserState.PS_START

        self.expected_parts = []

        self.active_part = None
        self.default_part = Part('_default', NullTarget())

        self._leftover_buffer = None

    def register(self, str name, object target):
        part = self._part_for(name)

        if part:
            part.add_target(target)
        else:
            self.expected_parts.append(Part(name, target))

    def set_active_part(self, part, str filename):
        self.active_part = part
        self.active_part.set_multipart_filename(filename)
        self.active_part.start()

    def unset_active_part(self):
        if self.active_part:
            self.active_part.finish()
        self.active_part = None

    def on_body(self, bytes value):
        if self.active_part and len(value) > 0:
            self.active_part.data_received(value)

    cdef _part_for(self, str name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    def data_received(self, bytes data):
        if not data:
            return 0

        cdef bytes chunk
        cdef size_t index

        if self._leftover_buffer:
            chunk = self._leftover_buffer + data
            index = len(self._leftover_buffer)
            self._leftover_buffer = None
        else:
            chunk = data
            index = 0

        return self._parse(chunk, index)

    def _parse(self, bytes chunk, size_t index):
        cdef size_t idx, buffer_start, chunk_len
        cdef size_t match_start, skip_count, matched_length
        cdef Byte byte
        cdef const Byte *chunk_ptr

        chunk_ptr = chunk
        chunk_len = len(chunk)
        buffer_start = 0

        idx = index
        while idx < chunk_len:
            byte = chunk_ptr[idx]

            if self.state == ParserState.PS_START:
                if byte == c_hyphen:
                    buffer_start = idx
                    self.state = ParserState.PS_STARTING_BOUNDARY
                elif byte == c_cr:
                    self.state = ParserState.PS_START_CR
                else:
                    self.mark_error()
                    return ErrorGroup.Delimiting + 1

            elif self.state == ParserState.PS_START_CR:
                if byte == c_lf:
                    self.state = ParserState.PS_START
                else:
                    self.mark_error()
                    return ErrorGroup.Delimiting + 4

            elif self.state == ParserState.PS_STARTING_BOUNDARY:
                if byte != c_hyphen:
                    self.mark_error()
                    return ErrorGroup.Delimiting + 2

                self.state = ParserState.PS_READING_BOUNDARY
            elif self.state == ParserState.PS_READING_BOUNDARY:
                if byte == c_cr:
                    self.state = ParserState.PS_ENDING_BOUNDARY

            elif self.state == ParserState.PS_ENDING_BOUNDARY:
                if byte != c_lf:
                    self.mark_error()
                    return ErrorGroup.Delimiting + 3

                # ensure we have read correct starting delimiter
                if b'\r\n' + chunk[buffer_start: idx + 1] != \
                        self.delimiter_finder.target:
                    self.mark_error()
                    return ErrorGroup.Delimiting + 5

                buffer_start = idx + 1

                self.state = ParserState.PS_READING_HEADER
            elif self.state == ParserState.PS_READING_HEADER:
                if byte == c_cr:
                    self.state = ParserState.PS_ENDING_HEADER

            elif self.state == ParserState.PS_ENDING_HEADER:
                if byte != c_lf:
                    self.mark_error()
                    return ErrorGroup.PartHeaders + 1
                
                m = Parser(policy=HTTP).parsestr(chunk[buffer_start: idx + 1].decode('utf-8'))

                if 'content-disposition' in m:
                    if not m.get_content_disposition() == 'form-data':
                        self.mark_error()
                        return ErrorGroup.PartHeaders + 1

                    params = m['content-disposition'].params
                    name = params.get('name')

                    if name:
                        part = self._part_for(name) or self.default_part
                        self.set_active_part(part, params.get('filename'))
                elif 'content-type' in m:
                    if self.active_part:
                        self.active_part.set_multipart_content_type(
                            m.get_content_type()
                        )

                buffer_start = idx + 1

                self.state = ParserState.PS_ENDED_HEADER
            elif self.state == ParserState.PS_ENDED_HEADER:
                if byte == c_cr:
                    self.state = ParserState.PS_ENDING_ALL_HEADERS
                else:
                    self.state = ParserState.PS_READING_HEADER

            elif self.state == ParserState.PS_ENDING_ALL_HEADERS:
                if byte != c_lf:
                    self.mark_error()
                    return ErrorGroup.PartHeaders + 2

                buffer_start = idx + 1

                self.state = ParserState.PS_READING_BODY
            elif self.state == ParserState.PS_READING_BODY:
                self.delimiter_finder.feed(byte)
                self.ender_finder.feed(byte)

                if self.delimiter_finder.found():
                    self.state = ParserState.PS_READING_HEADER

                    if idx + 1 < self.delimiter_length:
                        self.mark_error()
                        return ErrorGroup.Internal + 1

                    match_start = idx + 1 - self.delimiter_length

                    if match_start >= buffer_start:
                        try:
                            self.on_body(chunk[buffer_start: match_start])
                        except Exception:
                            self.mark_error()
                            raise

                        buffer_start = idx + 1
                    else:
                        self.mark_error()
                        return ErrorGroup.Internal + 2

                    self.unset_active_part()
                    self.delimiter_finder.reset()

                elif self.ender_finder.found():
                    self.state = ParserState.PS_END

                    if idx + 1 < self.ender_length:
                        self.mark_error()
                        return ErrorGroup.Internal + 3
                    match_start = idx + 1 - self.ender_length

                    if match_start >= buffer_start:
                        try:
                            self.on_body(chunk[buffer_start: match_start])
                        except Exception:
                            self.mark_error()
                            raise
                    else:
                        self.mark_error()
                        return ErrorGroup.Internal + 4

                    buffer_start = idx + 1

                    self.unset_active_part()
                    self.ender_finder.reset()

                else:
                    # This block is purely for speed optimization.
                    # The idea is to skip all data not containing the delimiter
                    # starting sequence '\r\n--' when we are not already in the
                    # middle of a potential delimiter.

                    if self.delimiter_finder.inactive():
                        skip_count = self.rewind_fast_forward(
                            chunk_ptr, idx + 1, chunk_len - 1
                        )
                        idx += skip_count

            elif self.state == ParserState.PS_END:
                return 0
            else:
                self.mark_error()
                return ErrorGroup.Internal + 5

            idx += 1

        if idx != chunk_len:
            self.mark_error()
            return ErrorGroup.Internal + 6

        if buffer_start > chunk_len:
            self.mark_error()
            return ErrorGroup.Internal + 7

        if self.state == ParserState.PS_READING_BODY:
            matched_length = max(
                self.delimiter_finder.matched_length(),
                self.ender_finder.matched_length()
            )
            match_start = idx - matched_length

            if match_start >= buffer_start + c_min_file_body_chunk_size:
                try:
                    self.on_body(chunk[buffer_start: match_start])
                except Exception:
                    self.mark_error()
                    raise

                buffer_start = match_start

        if idx - buffer_start > 0:
            self._leftover_buffer = chunk[buffer_start: idx]

        return 0

    # rewind_fast_forward searches for the '\r\n--' sequence in the provided
    # buffer. It returns the number of characters which can be skipped before
    # the delimiter starts (including potential 4-byte match). It may also
    # update Finder object states.

    cdef size_t rewind_fast_forward(
        self, const Byte *chunk_ptr, size_t pos_first, size_t pos_last
    ):
        cdef const Byte *ptr
        cdef const Byte *ptr_end
        cdef size_t skipped

        # we need at least 4 characters in buffer
        if pos_first + 3 > pos_last:
            return 0

        # calculate pointer to the first character of the buffer and the
        # pointer to a character after the end of the buffer
        ptr = chunk_ptr + pos_first + 3
        ptr_end = chunk_ptr + pos_last + 1
        skipped = 0

        # try to match starting from the 4th character of the multipart
        # delimiter (which always starts with a '\r\n--'). An additional
        # optimization is checking only every second character while no hyphen
        # is found.

        while True:
            if ptr >= ptr_end:
                # normalize pointer value because we could jump few characters
                # past the buffer end
                ptr = ptr_end - 1

                # if we iterated till the end of the buffer, we may need to
                # keep up to 3 characters in the buffer until next chunk
                # guess we will skip all characters in the buffer
                skipped = pos_last - pos_first + 1

                if ptr[0] == c_cr:
                    skipped = skipped - 1
                elif ptr[0] == c_lf and ptr[-1] == c_cr:
                    skipped = skipped - 2
                elif (
                    ptr[0] == c_hyphen
                    and ptr[-1] == c_lf
                    and ptr[-2] == c_cr
                ):
                    skipped = skipped - 3
                break

            if ptr[0] != c_hyphen:
                ptr += 2
            else:
                if ptr[-1] != c_hyphen:
                    ptr += 1
                else:
                    if ptr[-2] == c_lf and ptr[-3] == c_cr:
                        self.delimiter_finder.reset()
                        self.delimiter_finder.feed(c_cr)
                        self.delimiter_finder.feed(c_lf)
                        self.delimiter_finder.feed(c_hyphen)
                        self.delimiter_finder.feed(c_hyphen)

                        self.ender_finder.reset()
                        self.ender_finder.feed(c_cr)
                        self.ender_finder.feed(c_lf)
                        self.ender_finder.feed(c_hyphen)
                        self.ender_finder.feed(c_hyphen)

                        skipped = (ptr - chunk_ptr) - pos_first + 1

                        break
                    ptr += 4

        return skipped

    cdef mark_error(self):
        self.state = ParserState.PS_ERROR

        if self.active_part:
            self.active_part.finish()
