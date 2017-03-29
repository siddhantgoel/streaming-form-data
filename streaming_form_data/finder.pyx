cdef enum FinderState:
    START = -1
    WORKING = 0
    END = 1


cdef class Finder(object):
    cdef bytes target
    cdef long index
    cdef FinderState state

    def __init__(self, target):
        if len(target) < 1:
            raise ValueError('Empty values not allowed')

        self.target = target
        self.index = 0
        self.state = FinderState.START

    cpdef feed(self, long byte):
        if byte != self.target[self.index]:
            self.state = FinderState.START
            self.index = 0
        else:
            self.state = FinderState.WORKING
            self.index += 1

            if self.index == len(self.target):
                self.state = FinderState.END

    cpdef reset(self):
        self.state = FinderState.START
        self.index = 0

    @property
    def inactive(self):
        return self.state == FinderState.START

    @property
    def active(self):
        return self.state == FinderState.WORKING

    @property
    def found(self):
        return self.state == FinderState.END
