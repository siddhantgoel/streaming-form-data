# cython: language_level=3

import asyncio
from email.policy import HTTP
from email.parser import Parser

from streaming_form_data.targets import NullTarget, is_async_target


ctypedef unsigned char Byte  # noqa: E999


# useful constants

cdef int c_hyphen = 45
cdef int c_cr = 13
cdef int c_lf = 10
cdef int c_min_file_body_chunk_size = 1024


cdef enum FinderState:
    FS_START, FS_WORKING, FS_END


cpdef enum ErrorCode:
    """
    Error codes returned by the parser
    """

    # All good
    E_OK,

    # Internal program errors (asserts that should not fail)
    E_INTERNAL,

    # Problems with delimiting multipart stream into parts
    E_DELIMITING,

    # Problems with parsing specific part headers
    E_PART_HEADERS,

    # Problems with unregistered parts
    E_UNEXPECTED_PART


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


cdef class Finder:
    cdef bytes target
    cdef const Byte *target_ptr
    cdef size_t target_len, index
    cdef FinderState state

    def __init__(self, target):
        if len(target) < 1:
            raise ValueError("Empty values not allowed")

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


cdef class _Part:
    """
    A single part of a multipart/form-data request
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

    def is_sync(self):
        raise NotImplementedError()


cdef class Part(_Part):
    def start(self):
        for target in self.targets:
            target.start()

    def data_received(self, bytes chunk):
        for target in self.targets:
            target.data_received(chunk)

    def finish(self):
        for target in self.targets:
            target.finish()

    def is_sync(self):
        return True


cdef class AsyncPart(_Part):
    async def start(self):
        for target in self.targets:
            await target.start()

    async def data_received(self, bytes chunk):
        for target in self.targets:
            await target.data_received(chunk)

    async def finish(self):
        for target in self.targets:
            await target.finish()

    def is_sync(self):
        return False


cdef class _Parser:
    cdef ParserState state

    cdef Finder delimiter_finder, ender_finder
    cdef size_t delimiter_length, ender_length

    cdef object expected_parts
    cdef object active_part, default_part

    cdef bytes _leftover_buffer

    cdef bint strict
    cdef public str unexpected_part_name

    def __init__(self, bytes delimiter, bytes ender, bint strict):
        self.delimiter_finder = Finder(delimiter)
        self.ender_finder = Finder(ender)

        self.delimiter_length = len(delimiter)
        self.ender_length = len(ender)

        self.state = ParserState.PS_START

        self.expected_parts = []

        self.active_part = None
        self.default_part = Part("_default", NullTarget())

        self._leftover_buffer = None

        self.strict = strict
        self.unexpected_part_name = ""

    def register(self, str name, object target):
        part = self._part_for(name)

        if part:
            part.add_target(target)
        else:
            part_cls = AsyncPart if is_async_target(target) else Part
            self.expected_parts.append(part_cls(name, target))

    def set_active_part(self, part, str filename):
        self.active_part = part
        self.active_part.set_multipart_filename(filename)
        self.active_part.start()

    async def async_set_active_part(self, part, str filename):
        self.active_part = part
        self.active_part.set_multipart_filename(filename)
        await self.active_part.start()

    def unset_active_part(self):
        if self.active_part:
            self.active_part.finish()
        self.active_part = None

    async def async_unset_active_part(self):
        if self.active_part:
            await self.active_part.finish()
        self.active_part = None

    def on_body(self, bytes value):
        if self.active_part and len(value) > 0:
            self.active_part.data_received(value)

    async def async_on_body(self, bytes value):
        if self.active_part and len(value) > 0:
            await self.active_part.data_received(value)

    cdef _part_for(self, str name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    def data_received(self, bytes data):
        if not data:
            return ErrorCode.E_OK

        cdef bytes chunk
        cdef size_t index

        chunk, index = self.include_leftover_buffer(data)

        return self._parse(chunk, index)

    async def async_data_received(self, bytes data):
        if not data:
            return ErrorCode.E_OK

        cdef bytes chunk
        cdef size_t index

        chunk, index = self.include_leftover_buffer(data)

        return await self._parse(chunk, index)

    cdef include_leftover_buffer(self, bytes data):
        """
        Include any leftover buffer from the previous call in the current data and
        return the new buffer and its index.
        """

        cdef bytes chunk
        cdef size_t index

        if self._leftover_buffer:
            chunk = self._leftover_buffer + data
            index = len(self._leftover_buffer)
            self._leftover_buffer = None
        else:
            chunk = data
            index = 0

        return (chunk, index)

    cdef handle_ps_start(
        self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start
    ):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte == c_hyphen:
            buffer_start[0] = idx[0]
            self.state = ParserState.PS_STARTING_BOUNDARY
        elif byte == c_cr:
            self.state = ParserState.PS_START_CR
        else:
            self.mark_error()

    cdef handle_ps_start_cr(
        self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start
    ):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte == c_lf:
            self.state = ParserState.PS_START
        else:
            self.mark_error()

    cdef handle_ps_starting_boundary(
        self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start
    ):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte == c_hyphen:
            self.state = ParserState.PS_READING_BOUNDARY
        else:
            self.mark_error()

    cdef handle_ps_reading_boundary(
        self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start
    ):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte == c_cr:
            self.state = ParserState.PS_ENDING_BOUNDARY

    cdef handle_ps_ending_boundary(
        self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start
    ):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte != c_lf:
            self.mark_error()
            return

        # ensure we have read correct starting delimiter
        if b"\r\n" + chunk_ptr[buffer_start[0]: idx[0] + 1] != self.delimiter_finder.target:
            self.mark_error()
            return

        buffer_start[0] = idx[0] + 1
        self.state = ParserState.PS_READING_HEADER

    cdef handle_ps_reading_header(self, const Byte* chunk_ptr, size_t* idx, size_t* buffer_start):
        cdef Byte byte = chunk_ptr[idx[0]]

        if byte == c_cr:
            self.state = ParserState.PS_ENDING_HEADER

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
                self.handle_ps_start(chunk_ptr, &idx, &buffer_start)

                if self.has_error():
                    return ErrorCode.E_DELIMITING

            elif self.state == ParserState.PS_START_CR:
                self.handle_ps_start_cr(chunk_ptr, &idx, &buffer_start)

                if self.has_error():
                    return ErrorCode.E_DELIMITING

            elif self.state == ParserState.PS_STARTING_BOUNDARY:
                self.handle_ps_starting_boundary(chunk_ptr, &idx, &buffer_start)

                if self.has_error():
                    return ErrorCode.E_DELIMITING

            elif self.state == ParserState.PS_READING_BOUNDARY:
                self.handle_ps_reading_boundary(chunk_ptr, &idx, &buffer_start)

            elif self.state == ParserState.PS_ENDING_BOUNDARY:
                self.handle_ps_ending_boundary(chunk_ptr, &idx, &buffer_start)

                if self.has_error():
                    return ErrorCode.E_DELIMITING

            elif self.state == ParserState.PS_READING_HEADER:
                self.handle_ps_reading_header(chunk_ptr, &idx, &buffer_start)

            elif self.state == ParserState.PS_ENDING_HEADER:
                if byte != c_lf:
                    self.mark_error()
                    return ErrorCode.E_PART_HEADERS

                message = Parser(policy=HTTP).parsestr(
                    chunk[buffer_start: idx + 1].decode("utf-8")
                )

                if "content-disposition" in message:
                    if not message.get_content_disposition() == "form-data":
                        self.mark_error()
                        return ErrorCode.E_PART_HEADERS

                    params = message["content-disposition"].params
                    name = params.get("name")

                    if name:
                        part = self._part_for(name)
                        if part is None:
                            part = self.default_part
                            if self.strict:
                                self.unexpected_part_name = name
                                self.mark_error()
                                return ErrorCode.E_UNEXPECTED_PART

                        self.set_active_part(part, params.get("filename"))
                elif "content-type" in message:
                    if self.active_part:
                        self.active_part.set_multipart_content_type(
                            message.get_content_type()
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
                    return ErrorCode.E_PART_HEADERS

                buffer_start = idx + 1

                self.state = ParserState.PS_READING_BODY
            elif self.state == ParserState.PS_READING_BODY:
                self.delimiter_finder.feed(byte)
                self.ender_finder.feed(byte)

                if self.delimiter_finder.found():
                    self.state = ParserState.PS_READING_HEADER

                    if idx + 1 < self.delimiter_length:
                        self.mark_error()
                        return ErrorCode.E_INTERNAL

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
                        return ErrorCode.E_INTERNAL

                    self.unset_active_part()
                    self.delimiter_finder.reset()

                elif self.ender_finder.found():
                    self.state = ParserState.PS_END

                    if idx + 1 < self.ender_length:
                        self.mark_error()
                        return ErrorCode.E_INTERNAL
                    match_start = idx + 1 - self.ender_length

                    if match_start >= buffer_start:
                        try:
                            self.on_body(chunk[buffer_start: match_start])
                        except Exception:
                            self.mark_error()
                            raise
                    else:
                        self.mark_error()
                        return ErrorCode.E_INTERNAL

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
                return ErrorCode.E_OK
            else:
                self.mark_error()
                return ErrorCode.E_INTERNAL

            idx += 1

        if idx != chunk_len:
            self.mark_error()
            return ErrorCode.E_INTERNAL

        if buffer_start > chunk_len:
            self.mark_error()
            return ErrorCode.E_INTERNAL

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

        return ErrorCode.E_OK

    cdef size_t rewind_fast_forward(
        self, const Byte *chunk_ptr, size_t pos_first, size_t pos_last
    ):
        """
        Return the number of characters that can be skipped before the delimiter starts
        (including potential 4-byte match). It may also update Finder object states.
        """

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
            if self.active_part.is_sync():
                self.active_part.finish()
            else:
                asyncio.get_event_loop().call_soon_threadsafe(self.active_part.finish())

    cdef has_error(self):
        return self.state == ParserState.PS_ERROR
