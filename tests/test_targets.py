import os.path
import tempfile
from unittest import TestCase

from streaming_form_data.targets import (BaseTarget, FileTarget, NullTarget,
                                         ValueTarget)
from streaming_form_data.validators import MaxSizeValidator, ValidationError


class NullTargetTestCase(TestCase):
    def test_basic(self):
        target = NullTarget()

        target.multipart_filename = 'file001.txt'

        target.start()
        self.assertEqual(target.multipart_filename, 'file001.txt')

        target.data_received(b'hello')

        target.finish()

        self.assertEqual(target.multipart_filename, 'file001.txt')

    def test_not_sent(self):
        target = NullTarget()
        self.assertTrue(target.multipart_filename is None)


class ValueTargetTestCase(TestCase):
    def test_basic(self):
        target = ValueTarget()
        self.assertEqual(target.value, b'')

        target.multipart_filename = None

        target.start()
        self.assertTrue(target.multipart_filename is None)
        self.assertEqual(target.value, b'')

        target.data_received(b'hello')
        target.data_received(b' ')
        target.data_received(b'world')

        target.finish()

        self.assertTrue(target.multipart_filename is None)
        self.assertEqual(target.value, b'hello world')

    def test_not_sent(self):
        target = ValueTarget()
        self.assertEqual(target.value, b'')
        self.assertTrue(target.multipart_filename is None)

    def test_total_size_validator(self):
        target = ValueTarget(validators=(MaxSizeValidator(10),))

        self.assertEqual(target.value, b'')

        target.start()

        target.data_received(b'hello')
        target.data_received(b' ')

        self.assertRaises(ValidationError, target.data_received, b'world')


class FileTargetTestCase(TestCase):
    def test_basic(self):
        filename = os.path.join(tempfile.gettempdir(), 'file.txt')

        target = FileTarget(filename)

        target.multipart_filename = 'file001.txt'

        target.start()
        self.assertEqual(target.filename, filename)
        self.assertEqual(target.multipart_filename, 'file001.txt')
        self.assertTrue(os.path.exists(filename))

        target.data_received(b'hello')
        target.data_received(b' ')
        target.data_received(b'world')

        target.finish()

        self.assertTrue(os.path.exists(filename))

        self.assertEqual(target.filename, filename)
        self.assertEqual(target.multipart_filename, 'file001.txt')

        with open(filename, 'rb') as file_:
            self.assertEqual(file_.read(), b'hello world')

    def test_not_sent(self):
        filename = os.path.join(tempfile.gettempdir(), 'file_not_sent.txt')

        target = FileTarget(filename)

        self.assertFalse(os.path.exists(filename))

        self.assertEqual(target.filename, filename)
        self.assertTrue(target.multipart_filename is None)


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


class CustomTargetTestCase(TestCase):
    def test_basic(self):
        target = CustomTarget()
        self.assertEqual(target.value, b'')

        target.multipart_filename = 'file.txt'
        self.assertEqual(target._started, False)
        self.assertEqual(target._finished, False)

        target.start()
        target._started = True
        self.assertEqual(target.multipart_filename, 'file.txt')
        self.assertEqual(target.value, b'[start]')

        target.data_received(b'chunk1')
        target.data_received(b'chunk2')
        self.assertEqual(target.value, b'[start] chunk1 chunk2')
        target.data_received(b'chunk3')

        target.finish()
        target._finished = True

        self.assertEqual(target.multipart_filename, 'file.txt')
        self.assertEqual(target.value,
                         b'[start] chunk1 chunk2 chunk3 [finish]')
        self.assertEqual(target._started, True)
        self.assertEqual(target._finished, True)

    def test_not_sent(self):
        target = CustomTarget()
        self.assertEqual(target.value, b'')
        self.assertTrue(target.multipart_filename is None)
