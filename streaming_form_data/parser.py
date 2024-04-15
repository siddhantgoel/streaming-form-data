from email.message import EmailMessage
from typing import Mapping

from streaming_form_data._parser import ErrorGroup, _Parser  # type: ignore
from streaming_form_data.targets import BaseTarget


class ParseFailedException(Exception):
    pass


class UnexpectedPartException(ParseFailedException):
    def __init__(self, message, part_name):
        super().__init__(message)
        self.part_name = part_name


def parse_content_boundary(headers: Mapping[str, str]) -> bytes:
    """
    Return the content boundary value as extracted from the Content-Type header
    """

    content_type = None

    for key in headers.keys():
        if key.lower() == "content-type":
            content_type = headers.get(key)
            break

    if not content_type:
        raise ParseFailedException("Missing Content-Type header")

    message = EmailMessage()
    message["content-type"] = content_type

    if message.get_content_type() != "multipart/form-data":
        raise ParseFailedException("Content-Type is not multipart/form-data")

    boundary = message.get_boundary()
    if not boundary:
        raise ParseFailedException("Boundary not found")

    return boundary.encode("utf-8")


class StreamingFormDataParser:
    def __init__(self, headers: Mapping[str, str], strict: bool = False):
        self.headers = headers

        raw_boundary = parse_content_boundary(headers)

        delimiter = b"\r\n--" + raw_boundary + b"\r\n"
        ender = b"\r\n--" + raw_boundary + b"--"

        self._parser = _Parser(delimiter, ender, strict)

        self._running = False

    def register(self, name: str, target: BaseTarget):
        """
        Register a target for the given part name
        """

        if self._running:
            raise ParseFailedException(
                "Registering parts not allowed while parser is running"
            )

        self._parser.register(name, target)

    def data_received(self, data: bytes):
        """
        Feed data to the parser synchronously
        """

        if not self._running:
            self._running = True

        error_code = self._parser.data_received(data)

        self._check(error_code)

    async def async_data_received(self, data: bytes):
        """
        Feed data to the parser asynchronously
        """

        if not self._running:
            self._running = True

        error_code = await self._parser.data_received(data)

        self._check(error_code)

    def _check(self, error_code: int):
        if error_code == 0:
            return

        if ErrorGroup.Internal <= error_code < ErrorGroup.Delimiting:
            message = "internal errors"
        elif ErrorGroup.Delimiting <= error_code < ErrorGroup.PartHeaders:
            message = "delimiting multipart stream into parts"
        elif ErrorGroup.PartHeaders <= error_code < ErrorGroup.UnexpectedPart:
            message = "parsing specific part headers"
        elif ErrorGroup.UnexpectedPart == error_code:
            part = self._parser.unexpected_part_name
            raise UnexpectedPartException(
                f"parsing unexpected part '{part}' in strict mode", part
            )

        raise ParseFailedException(
            "_parser.data_received failed with {}".format(message)
        )
