import os.path
import tempfile
from unittest import TestCase

from streaming_form_data.targets import ValueTarget, FileTarget


class ValueTargetTestCase(TestCase):
    def test_basic(self):
        target = ValueTarget()
        self.assertEqual(target.value, b'')

        target.start()
        self.assertEqual(target.value, b'')

        target.data_received(b'hello')
        target.data_received(b' ')
        target.data_received(b'world')

        self.assertEqual(target.value, b'hello world')


class FileTargetTestCase(TestCase):
    def test_basic(self):
        filename = os.path.join(tempfile.gettempdir(), 'file.txt')

        target = FileTarget(filename)

        target.start()
        self.assertTrue(os.path.exists(filename))

        target.data_received(b'hello')
        target.data_received(b' ')
        target.data_received(b'world')

        target.finish()
        self.assertTrue(os.path.exists(filename))

        with open(filename, 'rb') as file_:
            self.assertEqual(file_.read(), b'hello world')
