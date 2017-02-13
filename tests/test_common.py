from unittest import TestCase

from streaming_form_data.common import Finder


class FinderTestCase(TestCase):
    def test_empty_string(self):
        finder = Finder('')

        self.assertFalse(finder.finding)
        self.assertTrue(finder.found)

    def test_single_character(self):
        finder = Finder('x')

        self.assertFalse(finder.finding)
        self.assertFalse(finder.found)

        finder.feed('x')
        self.assertFalse(finder.finding)
        self.assertTrue(finder.found)

    def test_basic(self):
        finder = Finder('hello')

        self.assertFalse(finder.finding)
        self.assertFalse(finder.found)

        finder.feed('h')
        self.assertTrue(finder.finding)
        self.assertFalse(finder.found)

        for char in ('e', 'l', 'l'):
            finder.feed(char)
            self.assertTrue(finder.finding)
            self.assertFalse(finder.found)

        finder.feed('o')
        self.assertFalse(finder.finding)
        self.assertTrue(finder.found)

        finder.reset()
        self.assertFalse(finder.finding)
        self.assertFalse(finder.found)

    def test_invalid_input(self):
        finder = Finder('abc')

        self.assertFalse(finder.finding)
        self.assertFalse(finder.found)

        finder.feed('x')
        self.assertFalse(finder.finding)
        self.assertFalse(finder.found)

        for char in ('a', 'b'):
            finder.feed(char)
            self.assertTrue(finder.finding)
            self.assertFalse(finder.found)

        finder.feed('c')
        self.assertFalse(finder.finding)
        self.assertTrue(finder.found)
