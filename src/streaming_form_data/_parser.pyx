# cython: language_level=3

from email.policy import HTTP
from email.parser import Parser

from streaming_form_data.targets import NullTarget


ctypedef unsigned char Byte


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
# 400..499: problems with unregistered parts
cpdef enum ErrorGroup:
    Internal = 100
    Delimiting = 200
    PartHeaders = 300
    UnexpectedPart = 400

# Scanner Actions
cdef enum Action:
    ACT_CONTINUE,
    ACT_DONE,
    ACT_EMIT_BODY,
    ACT_PART_START,
    ACT_PART_END,
    ACT_ERROR


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
    """One part of a multipart/form-data request"""

    cdef public str name
    cdef list targets

    def __init__(self, str name, object target):
        self.name = name
        self.targets = [target]

    def add_target(self, object target):
        self.targets.append(target)

    def set_multipart_filename(self, str value):
        for target in self.targets:
            target.set_multipart_filename(value)

    def set_multipart_content_type(self, str value):
        for target in self.targets:
            target.set_multipart_content_type(value)

    def start(self):
        for target in self.targets:
            target.start()

    def data_received(self, bytes chunk):
        for target in self.targets:
            target.data_received(chunk)

    def finish(self):
        for target in self.targets:
            target.finish()

    async def astart(self):
        for target in self.targets:
            await target.astart()

    async def adata_received(self, bytes chunk):
        for target in self.targets:
            await target.adata_received(chunk)

    async def afinish(self):
        for target in self.targets:
            await target.afinish()


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
    cdef bytes _emit_data

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
        self.default_part = Part('_default', NullTarget())

        self._leftover_buffer = None
        self._emit_data = None

        self.strict = strict
        self.unexpected_part_name = ''

    def register(self, str name, object target):
        part = self._part_for(name)

        if part:
            part.add_target(target)
        else:
            self.expected_parts.append(Part(name, target))

    # Helper to setup active part (called internally during scan)
    cdef _set_active_part(self, part, str filename):
        self.active_part = part
        self.active_part.set_multipart_filename(filename)
        # We don't call start() here, we let the caller do it based on return action

    cdef _part_for(self, str name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    def data_received(self, bytes data):
        return self._run_loop(data, is_async=False)

    async def adata_received(self, bytes data):
        ret = self._run_loop(data, is_async=True)
        # If the return is an int (status code), return it directly.
        # If it is a coroutine (from async target action), await it.
        if type(ret) is int:
            return ret
        return await ret

    # Combined loop runner (Handles Sync/Async dispatch)
    def _run_loop(self, bytes data, bint is_async):
        if not data:
            return 0

        cdef bytes chunk
        cdef size_t index
        cdef size_t buffer_start
        cdef Action action

        if self._leftover_buffer:
            chunk = self._leftover_buffer + data
            index = len(self._leftover_buffer)
            # Important: When we have leftover buffer, we start scanning at 'index'
            # (to avoid re-scanning bytes and corrupting state), but the buffer 
            # we want to potentially emit starts at 0.
            buffer_start = 0 
            self._leftover_buffer = None
        else:
            chunk = data
            index = 0
            buffer_start = 0

        # Loop processing via _scan
        while True:
            action = self._scan(chunk, &index, &buffer_start)
            
            if action == ACT_CONTINUE:
                continue
            
            elif action == ACT_DONE:
                break
                
            elif action == ACT_EMIT_BODY:
                if self.active_part:
                    if is_async:
                        return self._await_action(self.active_part.adata_received(self._emit_data), chunk, index, buffer_start, is_async=True)
                    else:
                        self.active_part.data_received(self._emit_data)
                self._emit_data = None
                
            elif action == ACT_PART_START:
                if self.active_part:
                    if is_async:
                        return self._await_action(self.active_part.astart(), chunk, index, buffer_start, is_async=True)
                    else:
                        self.active_part.start()
            
            elif action == ACT_PART_END:
                if self.active_part:
                    if is_async:
                        return self._await_action(self.active_part.afinish(), chunk, index, buffer_start, is_async=True)
                    else:
                        self.active_part.finish()
                    self.active_part = None
            
            elif action == ACT_ERROR:
                if self.active_part:
                    if is_async:
                        return self._await_action(self.active_part.afinish(), chunk, index, buffer_start, is_async=True)
                    else:
                        self.active_part.finish()
                return self._get_error_code()

        return 0

    # Helper for async recursion to keep the loop going after an await
    async def _await_action(self, coro, bytes chunk, size_t index, size_t buffer_start, bint is_async):
        await coro
        self._emit_data = None # Clear data if it was used
        
        # Resume loop
        cdef Action action
        while True:
            action = self._scan(chunk, &index, &buffer_start)
            
            if action == ACT_CONTINUE:
                continue
            elif action == ACT_DONE:
                break
            elif action == ACT_EMIT_BODY:
                if self.active_part:
                    await self.active_part.adata_received(self._emit_data)
                self._emit_data = None
            elif action == ACT_PART_START:
                if self.active_part:
                    await self.active_part.astart()
            elif action == ACT_PART_END:
                if self.active_part:
                    await self.active_part.afinish()
                    self.active_part = None
            elif action == ACT_ERROR:
                if self.active_part:
                    await self.active_part.afinish()
                return self._get_error_code()
        return 0

    cdef int _get_error_code(self):
        return self._error_code

    cdef int _error_code

    # The core state machine
    cdef Action _scan(self, bytes chunk, size_t *index_ptr, size_t *buffer_start_ptr):
        cdef size_t idx, buffer_start, chunk_len
        cdef size_t match_start, skip_count, matched_length
        cdef Byte byte
        cdef const Byte *chunk_ptr

        chunk_ptr = chunk
        chunk_len = len(chunk)
        
        buffer_start = buffer_start_ptr[0]
        idx = index_ptr[0]

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
                    self._error_code = ErrorGroup.Delimiting + 1
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

            elif self.state == ParserState.PS_START_CR:
                if byte == c_lf:
                    self.state = ParserState.PS_START
                else:
                    self.mark_error()
                    self._error_code = ErrorGroup.Delimiting + 4
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

            elif self.state == ParserState.PS_STARTING_BOUNDARY:
                if byte != c_hyphen:
                    self.mark_error()
                    self._error_code = ErrorGroup.Delimiting + 2
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR
                self.state = ParserState.PS_READING_BOUNDARY

            elif self.state == ParserState.PS_READING_BOUNDARY:
                if byte == c_cr:
                    self.state = ParserState.PS_ENDING_BOUNDARY

            elif self.state == ParserState.PS_ENDING_BOUNDARY:
                if byte != c_lf:
                    self.mark_error()
                    self._error_code = ErrorGroup.Delimiting + 3
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

                if b'\r\n' + chunk[buffer_start: idx + 1] != self.delimiter_finder.target:
                    self.mark_error()
                    self._error_code = ErrorGroup.Delimiting + 5
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

                buffer_start = idx + 1
                self.state = ParserState.PS_READING_HEADER

            elif self.state == ParserState.PS_READING_HEADER:
                if byte == c_cr:
                    self.state = ParserState.PS_ENDING_HEADER

            elif self.state == ParserState.PS_ENDING_HEADER:
                if byte != c_lf:
                    self.mark_error()
                    self._error_code = ErrorGroup.PartHeaders + 1
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

                message = Parser(policy=HTTP).parsestr(
                    chunk[buffer_start: idx + 1].decode('utf-8')
                )

                if 'content-disposition' in message:
                    if not message.get_content_disposition() == 'form-data':
                        self.mark_error()
                        self._error_code = ErrorGroup.PartHeaders + 1
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_ERROR

                    params = message['content-disposition'].params
                    name = params.get('name')

                    if name:
                        part = self._part_for(name)
                        if part is None:
                            part = self.default_part
                            if self.strict:
                                self.unexpected_part_name = name
                                self.mark_error()
                                self._error_code = ErrorGroup.UnexpectedPart
                                index_ptr[0] = idx + 1
                                buffer_start_ptr[0] = buffer_start
                                return ACT_ERROR

                        self._set_active_part(part, params.get('filename'))
                        buffer_start = idx + 1
                        self.state = ParserState.PS_ENDED_HEADER
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_PART_START 

                elif 'content-type' in message:
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
                    self._error_code = ErrorGroup.PartHeaders + 2
                    index_ptr[0] = idx + 1
                    buffer_start_ptr[0] = buffer_start
                    return ACT_ERROR

                buffer_start = idx + 1
                self.state = ParserState.PS_READING_BODY

            elif self.state == ParserState.PS_READING_BODY:
                self.delimiter_finder.feed(byte)
                self.ender_finder.feed(byte)

                if self.delimiter_finder.found():
                    self.state = ParserState.PS_READING_HEADER

                    if idx + 1 < self.delimiter_length:
                        self.mark_error()
                        self._error_code = ErrorGroup.Internal + 1
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_ERROR

                    match_start = idx + 1 - self.delimiter_length

                    if match_start >= buffer_start:
                        self._emit_data = chunk[buffer_start: match_start]
                        self.delimiter_finder.reset()
                        buffer_start = idx + 1
                        index_ptr[0] = idx + 1 
                        buffer_start_ptr[0] = buffer_start
                        self._pending_finish = True
                        return ACT_EMIT_BODY
                    else:
                        self.delimiter_finder.reset()
                        buffer_start = idx + 1
                        self._pending_finish = True
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_PART_END

                elif self.ender_finder.found():
                    self.state = ParserState.PS_END

                    if idx + 1 < self.ender_length:
                        self.mark_error()
                        self._error_code = ErrorGroup.Internal + 3
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_ERROR
                        
                    match_start = idx + 1 - self.ender_length

                    if match_start >= buffer_start:
                        self._emit_data = chunk[buffer_start: match_start]
                        self.ender_finder.reset()
                        buffer_start = idx + 1
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        self._pending_finish = True
                        return ACT_EMIT_BODY
                    else:
                        self.ender_finder.reset()
                        buffer_start = idx + 1
                        self._pending_finish = True
                        index_ptr[0] = idx + 1
                        buffer_start_ptr[0] = buffer_start
                        return ACT_PART_END

                else:
                    if self.delimiter_finder.inactive():
                        skip_count = self.rewind_fast_forward(
                            chunk_ptr, idx + 1, chunk_len - 1
                        )
                        idx += skip_count
            
            if self._pending_finish:
                 self._pending_finish = False
                 index_ptr[0] = idx
                 buffer_start_ptr[0] = buffer_start
                 return ACT_PART_END

            elif self.state == ParserState.PS_END:
                index_ptr[0] = idx + 1
                buffer_start_ptr[0] = buffer_start
                return ACT_DONE 
            
            elif self.state == ParserState.PS_ERROR:
                self._error_code = ErrorGroup.Internal + 5
                index_ptr[0] = idx + 1
                buffer_start_ptr[0] = buffer_start
                return ACT_ERROR

            idx += 1

        if idx != chunk_len:
            self.mark_error()
            self._error_code = ErrorGroup.Internal + 6
            index_ptr[0] = idx
            buffer_start_ptr[0] = buffer_start
            return ACT_ERROR

        if buffer_start > chunk_len:
            self.mark_error()
            self._error_code = ErrorGroup.Internal + 7
            index_ptr[0] = idx
            buffer_start_ptr[0] = buffer_start
            return ACT_ERROR

        if self.state == ParserState.PS_READING_BODY:
            matched_length = max(
                self.delimiter_finder.matched_length(),
                self.ender_finder.matched_length()
            )
            match_start = idx - matched_length

            if match_start >= buffer_start + c_min_file_body_chunk_size:
                self._emit_data = chunk[buffer_start: match_start]
                buffer_start = match_start
                index_ptr[0] = idx
                buffer_start_ptr[0] = buffer_start
                return ACT_EMIT_BODY

        if idx - buffer_start > 0:
            self._leftover_buffer = chunk[buffer_start: idx]

        if self._pending_finish:
             self._pending_finish = False
             return ACT_PART_END

        if self._emit_data is not None:
             index_ptr[0] = idx
             buffer_start_ptr[0] = buffer_start
             return ACT_EMIT_BODY

        index_ptr[0] = idx
        buffer_start_ptr[0] = buffer_start
        return ACT_DONE

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
    
    cdef bint _pending_finish