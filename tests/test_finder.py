from unittest import TestCase

from streaming_form_data._parser import Finder


class FinderTestCase(TestCase):
    def test_invalid_init(self):
        self.assertRaises(TypeError, Finder, None)
        self.assertRaises(TypeError, Finder, 'abc')
        self.assertRaises(TypeError, Finder, 123)
        self.assertRaises(TypeError, Finder, 123.456)
        self.assertRaises(TypeError, Finder, [123, 456])
        self.assertRaises(TypeError, Finder, (123, 456))

        self.assertRaises(ValueError, Finder, b'')

    def test_init(self):
        finder = Finder(b'hello')

        self.assertEqual(finder.target, b'hello')
        self.assertTrue(finder.inactive())
        self.assertFalse(finder.found())

    def test_single_byte(self):
        finder = Finder(b'-')

        self.assertTrue(finder.inactive())

        finder.feed(45)
        self.assertTrue(finder.found())

    def test_normal(self):
        finder = Finder(b'hello')

        self.assertTrue(finder.inactive())

        for byte in [104, 101, 108, 108]:
            finder.feed(byte)

            self.assertTrue(finder.active())
            self.assertFalse(finder.found())

        finder.feed(111)

        self.assertFalse(finder.active())
        self.assertTrue(finder.found())

    def test_wrong_byte(self):
        finder = Finder(b'hello')
        self.assertTrue(finder.inactive())

        finder.feed(104)
        self.assertTrue(finder.active())

        finder.feed(42)
        self.assertTrue(finder.inactive())
