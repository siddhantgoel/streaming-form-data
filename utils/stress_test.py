import math
import os
from io import BytesIO
from itertools import chain
from unittest import TestCase
import random

from requests_toolbelt import MultipartEncoder

from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import ValueTarget


def get_random_bytes(size, seed):
    random.seed(seed)

    return os.urandom(size)


def get_hyphens_crlfs(size, seed):
    random.seed(seed)
    return random.choice([b"\r", b"\n", b"-"], size, p=[0.25, 0.25, 0.5]).tobytes()


def is_prime(n):
    if n % 2 == 0 and n > 2:
        return False
    return all(n % i for i in range(3, int(math.sqrt(n)) + 1, 2))


def is_power_of(x, base):
    n = x
    while n:
        if n == 1:
            return True
        if n % base:
            return False
        n /= base
    raise Exception(
        "is_power_of: unexpected result with x = " + str(x) + " and base = " + str(base)
    )


def is_square(n):
    sq = int(math.sqrt(n))
    return sq * sq == n


def is_multiple(n, base):
    return n % base == 0


def is_useful_number(n):
    """
    This function returns True if the number can be used for testing the Parser
    with the chunk size of transferred data size. Most of these numbers will be
    prime numbers +- 1.
    The main idea of this function is to help speedup stress testing by using a
    wide range of algorithm parameters without the need to use all possible
    values.
    """
    if n <= 1000 and is_prime(n):
        return True

    if is_power_of(n, 2) or is_power_of(n - 1, 2) or is_power_of(n + 1, 2):
        return True

    if is_power_of(n, 10) or is_power_of(n - 1, 10) or is_power_of(n + 1, 10):
        return True

    if is_multiple(n, 1024) or is_multiple(n - 1, 1024) or is_multiple(n + 1, 1024):
        return True

    if is_multiple(n, 1000) or is_multiple(n - 1, 1000) or is_multiple(n + 1, 1000):
        return True

    if is_square(n):
        return True

    if n <= 64:
        return True

    return False


def is_more_useful_number(n):
    """
    This function is the same like is_useful_number but it choses less numbers.
    The function is written to be used in O(n^2) algorithm where both chunk
    size and file size vary.
    """
    if n <= 100 and is_prime(n):
        return True

    if is_power_of(n, 2) or is_power_of(n - 1, 2) or is_power_of(n + 1, 2):
        return True

    if is_power_of(n, 10) or is_power_of(n - 1, 10) or is_power_of(n + 1, 10):
        return True

    if is_multiple(n, 4 * 1024) or is_multiple(n - 1, 1024) or is_multiple(n + 1, 1024):
        return True

    if is_multiple(n, 5 * 1000) or is_multiple(n - 1, 1000) or is_multiple(n + 1, 1000):
        return True

    if is_square(n) and n <= 100:
        return True

    if n <= 32:
        return True

    return False


def get_max_useful_number():
    """
    This number was chosen heuristically. It needs to be big enough to test
    better, but small enough so that the test suite doesn't take forever.

    The number is bigger than 64K (2^16), and it covers the next
    10K-multiple numbers +- 1.
    """
    return 70 * 1000 + 1


def get_useful_numbers(short_list=False):
    # chosen heuristically
    upper_limit = 17000 if short_list else get_max_useful_number()

    check_func = is_more_useful_number if short_list else is_useful_number

    return [x for x in range(1, upper_limit + 1) if check_func(x)]


class ParserTestCaseBase(TestCase):
    def subTest(
        self,
        test_idx,
        test_name,
        chunksize,
        original_data,
        content_type,
        multipart_data,
        multipart_filename,
    ):
        print(
            test_idx,
            "; name: ",
            test_name,
            "; data_size: ",
            len(original_data),
            "; chunksize: ",
            chunksize,
        )

        parser = StreamingFormDataParser(headers={"Content-Type": content_type})

        target = ValueTarget()
        parser.register("file", target)

        remaining = len(multipart_data)
        offset = 0

        while remaining:
            step_size = min(remaining, chunksize)
            parser.data_received(multipart_data[offset : offset + step_size])
            offset += step_size
            remaining -= step_size

        self.assertEqual(offset, len(multipart_data))
        self.assertEqual(target.multipart_filename, multipart_filename)
        self.assertEqual(target._started, True)
        self.assertEqual(target._finished, True)

        result = target.value
        self.assertEqual(len(result), len(original_data))
        self.assertEqual(result, original_data)


class DifferentChunksTestCase(ParserTestCaseBase):
    def test_basic_last_attach(self):
        data = get_random_bytes(1024 * 1024, 159)
        self.do_test(data, "random_bytes", True)

    def test_basic_first_attach(self):
        data = get_random_bytes(1024 * 1024, 259)
        self.do_test(data, "random_bytes", False)

    def test_special_chars_last_attach(self):
        data = get_hyphens_crlfs(1024 * 1024, 359)
        self.do_test(data, "hyphens_crlfs", True)

    def test_special_chars_first_attach(self):
        data = get_hyphens_crlfs(1024 * 1024, 459)
        self.do_test(data, "hyphens_crlfs", False)

    def do_test(self, original_data, dataset_name, last_part):
        with BytesIO(original_data) as dataset_:
            if last_part:
                fields = {
                    "name": "hello world",
                    "file": ("file.dat", dataset_, "binary/octet-stream"),
                }
            else:
                fields = {
                    "file": ("file.dat", dataset_, "binary/octet-stream"),
                    "name": "hello world",
                }

            encoder = MultipartEncoder(fields=fields)
            content_type = encoder.content_type
            multipart_data = encoder.to_string()

        useful_numbers = get_useful_numbers()
        self.assertEqual(len(useful_numbers), 880)

        idx = 0
        for chunksize in useful_numbers:
            idx += 1

            self.subTest(
                idx,
                "DifferentChunks." + dataset_name,
                chunksize,
                original_data,
                content_type,
                multipart_data,
                "file.dat",
            )

        self.assertEqual(idx, len(useful_numbers))


class DifferentFileSizesTestCase(ParserTestCaseBase):
    def test_basic(self):
        data = get_random_bytes(get_max_useful_number(), 137)
        self.do_test(data, "random_bytes")

    def test_special_chars(self):
        data = get_hyphens_crlfs(get_max_useful_number(), 237)
        self.do_test(data, "hyphens_crlfs")

    def do_test(self, data, dataset_name):
        useful_numbers = get_useful_numbers()

        idx = 0
        for file_size in chain([0], useful_numbers):
            idx += 1

            original_data = data[0:file_size]
            with BytesIO(data[0:file_size]) as dataset_:
                fields = {"file": ("file.dat", dataset_, "binary/octet-stream")}
                encoder = MultipartEncoder(fields=fields)
                content_type = encoder.content_type
                multipart_data = encoder.to_string()

            self.subTest(
                idx,
                "DifferentFileSizes." + dataset_name,
                1024,
                original_data,
                content_type,
                multipart_data,
                "file.dat",
            )

        self.assertEqual(idx, len(useful_numbers) + 1)


class StressMatrixTestCase(ParserTestCaseBase):
    def test_basic(self):
        data = get_random_bytes(get_max_useful_number(), 171)
        self.do_test(data, "random_bytes")

    def do_test(self, data, dataset_name):
        useful_numbers = get_useful_numbers(short_list=True)
        self.assertEqual(len(useful_numbers), 140)

        idx = 0
        for file_size in chain([0], useful_numbers):
            original_data = data[0:file_size]
            with BytesIO(data[0:file_size]) as dataset_:
                fields = {"file": ("file.dat", dataset_, "binary/octet-stream")}
                encoder = MultipartEncoder(fields=fields)
                content_type = encoder.content_type
                multipart_data = encoder.to_string()

            for chunksize in useful_numbers:
                if chunksize > file_size:
                    continue
                idx += 1

                self.subTest(
                    idx,
                    "StressMatrixTest." + dataset_name,
                    chunksize,
                    original_data,
                    content_type,
                    multipart_data,
                    "file.dat",
                )

        self.assertEqual(idx, len(useful_numbers) * (len(useful_numbers) + 1) / 2)
