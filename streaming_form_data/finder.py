from enum import Enum


class FinderState(Enum):
    START = -1
    WORKING = 0
    END = 1


class Finder(object):
    def __init__(self, target):
        if len(target) < 1:
            raise ValueError('Empty values not allowed')

        if not isinstance(target, bytes):
            raise TypeError('Only bytes allowed')

        self.target = target
        self.index = 0
        self.state = FinderState.START

    def feed(self, byte):
        if byte != self.target[self.index]:
            self.state = FinderState.START
            self.index = 0
        else:
            self.state = FinderState.WORKING
            self.index += 1

            if self.index == len(self.target):
                self.state = FinderState.END

    def reset(self):
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
