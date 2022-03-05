# cython: language_level=3

ctypedef unsigned char Byte # noqa: E999

# useful constants
cdef int c_hyphen = 45
cdef int c_cr = 13
cdef int c_lf = 10
cdef int c_min_file_body_chunk_size = 1024

# 100..199: internal program errors (asserts)
# 200..299: problems with delimiting multipart stream into parts
# 300..399: problems with parsing particular part headers
cpdef enum ErrorGroup:
    Internal = 100
    Delimiting = 200
    PartHeaders = 300


cdef enum FinderState:
    FS_START, FS_WORKING, FS_END

cdef class Finder:
    cdef bytes target
    cdef const Byte *target_ptr
    cdef size_t target_len, index
    cdef FinderState state

    cpdef feed(self, Byte byte)
    cdef reset(self)
    cpdef bint inactive(self)
    cpdef bint active(self)
    cpdef bint found(self)
    cdef size_t matched_length(self)

cdef class Part:
    cdef public str name
    cdef list targets

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

    cdef _part_for(self, str name)
    
    cdef size_t rewind_fast_forward(
        self, const Byte *chunk_ptr, size_t pos_first, size_t pos_last
    )

    cdef mark_error(self)