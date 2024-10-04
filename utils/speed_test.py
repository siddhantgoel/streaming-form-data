from io import BytesIO
from time import time

from numpy import random
from requests_toolbelt import MultipartEncoder

from streaming_form_data.parser import StreamingFormDataParser
from streaming_form_data.targets import BaseTarget, NullTarget


class DummyTarget(BaseTarget):
    def __init__(self, print_report, gather_data):
        self._print_report = print_report
        self._gather_data = gather_data
        self._values = []

    def start(self):
        if self._print_report:
            print("DummyTarget: start")

    def data_received(self, chunk):
        if self._print_report:
            print("DummyTarget: data_received:", len(chunk), "bytes")
        if self._gather_data:
            self._values.append(chunk)

    def finish(self):
        if self._print_report:
            print("DummyTarget: finish")

    def get_result(self):
        return b"".join(self._values)


def fill_bytes_random(size):
    random.seed(42)
    return random.bytes(size)


def main():
    print("Prepare data...")
    begin_time = time()

    kibibyte = 1024
    mebibyte = kibibyte * kibibyte
    filedata_size = 400 * mebibyte

    filedata = fill_bytes_random(filedata_size)

    with BytesIO(filedata) as fd:
        content_type = "binary/octet-stream"

        encoder = MultipartEncoder(fields={"file": ("file", fd, content_type)})
        headers = {"Content-Type": encoder.content_type}
        body = encoder.to_string()

    print_report = False
    gather_data = False

    if not gather_data:
        filedata = None  # free memory

    target = DummyTarget(print_report=print_report, gather_data=gather_data)

    parser = StreamingFormDataParser(headers)
    parser.register("name", NullTarget())
    parser.register("lines", NullTarget())
    parser.register("file", target)

    defaultChunksize = 32 * kibibyte
    position = 0
    body_length = len(body)
    remaining = body_length

    end_time = time()
    print("Data prepared")
    time_diff = end_time - begin_time
    print(
        "Preparation took: %.3f sec; speed: %.3f MB/s; body size: %.3f MB"
        % (
            time_diff,
            (body_length / time_diff / mebibyte if time_diff > 0 else 0),
            body_length / mebibyte,
        )
    )

    print("Begin test...")

    begin_time = time()

    while remaining > 0:
        chunksize = min(defaultChunksize, remaining)
        parser.data_received(body[position : position + chunksize])
        remaining -= chunksize
        position += chunksize

    end_time = time()

    print("End test")

    if gather_data:
        result = target.get_result()
        if result != filedata:
            print("-------------------------------------------")
            print(
                "ERROR! Decoded data mismatch! Orig size: ",
                len(filedata),
                "; got size:",
                len(result),
            )
            print("-------------------------------------------")
        if not target._finished:
            print("-------------------------------------------")
            print("ERROR! Data decoding is not complete!")
            print("-------------------------------------------")

    time_diff = end_time - begin_time
    print(
        "Test took: %.3f sec; speed: %.3f MB/s; body size: %.3f MB"
        % (
            time_diff,
            (body_length / time_diff / mebibyte if time_diff > 0 else 0),
            body_length / mebibyte,
        )
    )


if __name__ == "__main__":
    main()
