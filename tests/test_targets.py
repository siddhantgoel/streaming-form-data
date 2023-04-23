import os.path
import tempfile

import pytest

from streaming_form_data.targets import (
    BaseTarget,
    FileTarget,
    DirectoryTarget,
    NullTarget,
    ValueTarget,
    S3Target
)
from moto import mock_s3
import boto3
from unittest import TestCase

from streaming_form_data.validators import MaxSizeValidator, ValidationError


def test_null_target_filename_not_set():
    target = NullTarget()

    assert target.multipart_filename is None


def test_null_target_basic():
    target = NullTarget()

    target.multipart_filename = 'file001.txt'

    target.start()
    assert target.multipart_filename == 'file001.txt'

    target.data_received(b'hello')
    target.finish()

    assert target.multipart_filename == 'file001.txt'


def test_value_target_basic():
    target = ValueTarget()

    assert target.value == b''

    target.multipart_filename = None

    target.start()
    assert target.multipart_filename is None
    assert target.value == b''

    target.data_received(b'hello')
    target.data_received(b' ')
    target.data_received(b'world')

    target.finish()

    assert target.multipart_filename is None
    assert target.value == b'hello world'


def test_value_target_not_set():
    target = ValueTarget()

    assert target.multipart_filename is None
    assert target.value == b''


def test_value_target_total_size_validator():
    target = ValueTarget(validator=MaxSizeValidator(10))

    assert target.value == b''

    target.start()

    target.data_received(b'hello')
    target.data_received(b' ')

    with pytest.raises(ValidationError):
        target.data_received(b'world')


def test_file_target_basic():
    filename = os.path.join(tempfile.gettempdir(), 'file.txt')

    target = FileTarget(filename)

    target.multipart_filename = 'file001.txt'

    target.start()

    assert target.filename == filename
    assert target.multipart_filename == 'file001.txt'
    assert os.path.exists(filename)

    target.data_received(b'hello')
    target.data_received(b' ')
    target.data_received(b'world')

    target.finish()

    assert target.filename == filename
    assert target.multipart_filename == 'file001.txt'
    assert os.path.exists(filename)

    with open(filename, 'rb') as file_:
        assert file_.read() == b'hello world'


def test_file_target_not_set():
    filename = os.path.join(tempfile.gettempdir(), 'file_not_sent.txt')

    target = FileTarget(filename)

    assert not os.path.exists(filename)
    assert target.filename == filename
    assert target.multipart_filename is None


def test_directory_target_basic():
    directory_path = tempfile.gettempdir()

    target = DirectoryTarget(directory_path)

    first_path = os.path.join(directory_path, 'file001.txt')
    target.multipart_filename = 'file001.txt'

    target.start()

    assert target.directory_path == directory_path
    assert target.multipart_filename == 'file001.txt'
    assert os.path.exists(first_path)

    target.data_received(b'first')
    target.data_received(b' ')
    target.data_received(b'file')

    target.finish()

    second_path = os.path.join(directory_path, 'file002.txt')
    target.multipart_filename = 'file002.txt'

    target.start()

    assert target.directory_path == directory_path
    assert target.multipart_filename == 'file002.txt'
    assert os.path.exists(second_path)

    target.data_received(b'second')
    target.data_received(b' ')
    target.data_received(b'file')

    target.finish()

    assert target.directory_path == directory_path
    assert target.multipart_filenames == ['file001.txt', 'file002.txt']
    assert os.path.exists(first_path)
    assert os.path.exists(second_path)

    with open(first_path, 'rb') as file_:
        assert file_.read() == b'first file'

    with open(second_path, 'rb') as file_:
        assert file_.read() == b'second file'


def test_directory_target_not_set():
    directory_path = tempfile.gettempdir()

    target = DirectoryTarget(directory_path)

    assert target.directory_path == directory_path
    assert not target.multipart_filenames


def test_directory_target_path_traversal():
    directory_path = tempfile.gettempdir()

    target = DirectoryTarget(directory_path)

    right_path = os.path.join(directory_path, 'file_path_traversal.txt')
    wrong_path = os.path.join(directory_path, '../file_path_traversal.txt')
    target.multipart_filename = '../file_path_traversal.txt'

    target.start()

    assert target.directory_path == directory_path
    assert target.multipart_filename == 'file_path_traversal.txt'
    assert os.path.exists(right_path)
    assert not os.path.exists(wrong_path)

    target.data_received(b'my')
    target.data_received(b' ')
    target.data_received(b'file')

    target.finish()

    assert target.directory_path == directory_path
    assert target.multipart_filenames == ['file_path_traversal.txt']
    assert os.path.exists(right_path)
    assert not os.path.exists(wrong_path)

    with open(right_path, 'rb') as file_:
        assert file_.read() == b'my file'


class CustomTarget(BaseTarget):
    def __init__(self):
        super().__init__()
        self._values = []

    def start(self):
        self._values.append(b'[start]')

    def data_received(self, chunk):
        self._values.append(chunk)

    def finish(self):
        self._values.append(b'[finish]')

    @property
    def value(self):
        return b' '.join(self._values)


def test_custom_target_basic():
    target = CustomTarget()

    assert target.value == b''

    target.multipart_filename = 'file.txt'

    assert not target._started
    assert not target._finished

    target.start()
    target._started = True

    assert target.multipart_filename == 'file.txt'
    assert target.value == b'[start]'

    target.data_received(b'chunk1')
    target.data_received(b'chunk2')

    assert target.value == b'[start] chunk1 chunk2'

    target.data_received(b'chunk3')

    target.finish()
    target._finished = True

    assert target.multipart_filename == 'file.txt'
    assert target.value == b'[start] chunk1 chunk2 chunk3 [finish]'
    assert target._started
    assert target._finished


def test_custom_target_not_sent():
    target = CustomTarget()

    assert target.value == b''
    assert target.multipart_filename is None


class TestS3TargetUpload(TestCase):

    mock_s3 = mock_s3()
    bucket_name = "test-bucket"
    client = boto3.client(service_name='s3')

    def setUp(self):
        self.mock_s3.start()

        # you can use boto3.client("s3") if you prefer
        self.client.create_bucket(Bucket=self.bucket_name)

    def tearDown(self):
        self.mock_s3.stop()

    def test(self):
        test_key = 'test.txt'
        path = f"s3://{self.bucket_name}/{test_key}"
        target = S3Target(
            path,
            'wb',
            transport_params={'client': self.client},
        )

        target.start()

        target.data_received(b'my test')
        target.data_received(b' ')
        target.data_received(b'file')

        target.finish()

        resp = self.client.get_object(
            Bucket=self.bucket_name,
            Key=test_key
        )['Body'].read().decode('utf-8')

        self.assertEqual(resp, 'my test file')
