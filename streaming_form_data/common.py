class Finder(object):
    def __init__(self, target):
        self.target = target
        self.length = len(self.target)
        self.index = -1

    def feed(self, char):
        self.index += 1

        if self.index >= self.length:
            return

        if self.target[self.index] != char:
            self.index = -1
            if char == self.target[0]:
                self.feed(char)

    def reset(self):
        self.index = -1

    @property
    def finding(self):
        return self.index > -1 and self.index < self.length - 1

    @property
    def found(self):
        return self.index == self.length - 1
