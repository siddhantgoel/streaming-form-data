import cgi


crlf = b'\r\n'


class ParseFailedException(Exception):
    pass


def parse_content_boundary(headers):
    content_type = headers.get('Content-Type')
    if not content_type:
        raise ParseFailedException()

    value, params = cgi.parse_header(content_type)

    if not value or value.lower() != 'multipart/form-data':
        raise ParseFailedException()

    boundary = params.get('boundary')
    if not boundary:
        raise ParseFailedException()

    return boundary


class StreamingFormDataParser(object):
    def __init__(self, expected_parts, headers):
        self.expected_parts = expected_parts
        self.headers = headers

        self.__separator = b'--'
        self._boundary = parse_content_boundary(headers)
        self._delimiter = self.__separator + self._boundary + crlf
        self._ender = \
            self.__separator + self._boundary + self.__separator + crlf

        self._state = None
        self._active_part = None

        self.__leftover_chunk = None
        self.__headers = (b'Content-Disposition', b'Content-Type')

    @property
    def active_part(self):
        return self._active_part

    def _unset_active_part(self):
        if self._active_part:
            self._active_part.finish()
        self._active_part = None

    def _set_active_part(self, part):
        self._unset_active_part()
        self._active_part = part

    def data_received(self, chunk):
        if len(chunk) < len(self._boundary):
            raise ParseFailedException('Chunk size less than boundary')

        self._parse(chunk)

    def _part_for(self, name):
        for part in self.expected_parts:
            if part.name == name:
                return part

    def _is_header(self, line):
        for header in self.__headers:
            if line.startswith(header):
                return True
        return False

    def _parse(self, chunk):
        if self.__leftover_chunk:
            chunk = chunk + self.__leftover_chunk
            self.__leftover_chunk = None

        lines = chunk.split(crlf)

        for line in lines:
            if not line:
                continue
            elif self._is_boundary(line):
                self._unset_active_part()
            elif self._is_header(line):
                self._unset_active_part()

                value, params = cgi.parse_header(line)
                if value == 'Content-Disposition':
                    part = self._part_for(params['name'])
                    part.start()

                    self._set_active_part(part)
            else:
                if self.__separator in line:
                    index = line.index(self.__separator)
                    self._active_part.data_received(line[:index])

                    self.__leftover_chunk = line[index:]
                else:
                    self._active_part.data_received(line)

    def _is_boundary(self, line):
        return line == self._boundary
