import pytest

from streaming_form_data._parser import Finder


def test_invalid_init():
    for value in (None, "abc", 123, 123.456, [123, 456], (123, 456)):
        with pytest.raises(TypeError):
            Finder(value)

    with pytest.raises(ValueError):
        Finder(b"")


def test_init():
    finder = Finder(b"hello")

    assert finder.target == b"hello"
    assert finder.inactive()
    assert not finder.found()


def test_single_byte():
    finder = Finder(b"-")

    assert finder.inactive()

    finder.feed(ord("-"))
    assert finder.found()


def test_normal():
    finder = Finder(b"hello")

    assert finder.inactive()

    for byte in [ord("h"), ord("e"), ord("l"), ord("l")]:
        finder.feed(byte)

        assert finder.active()
        assert not finder.found()

    finder.feed(ord("o"))

    assert not finder.active()
    assert finder.found()


def test_wrong_byte():
    finder = Finder(b"hello")

    assert finder.inactive()

    finder.feed(ord("h"))
    assert finder.active()

    finder.feed(42)
    assert finder.inactive()
