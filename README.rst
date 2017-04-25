Streaming multipart/form-data parser
====================================

.. image:: https://travis-ci.org/siddhantgoel/streaming-form-data.svg?branch=master
    :target: https://travis-ci.org/siddhantgoel/streaming-form-data

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data


:code:`streaming_form_data` provides a Python parser for parsing
multipart/form-data input chunks. Chunk size is determined by the API user, but
currently there are no restrictions on what the size should be, since the parser
works byte-by-byte. Although, this also means that passing the entire input as a
single chunk should also work.

The main entry point is the :code:`StreamingFormDataParser` class, which expects
a dictionary of request :code:`headers`.

The parser is fed chunks of (byte) input, and takes action depending on what the
current byte is. In case it notices input that's expected, it passes on the
input to the configured :code:`Target`, which then decides what to do with it.
In case there's a part that we don't need, this input is simply discarded using
a :code:`NullTarget` object.

Currently three targets are included with this library - :code:`ValueTarget`,
:code:`FileTarget`, and :code:`SHA256Target`. :code:`ValueTarget` stores the
input in memory, and :code:`FileTarget` pipes the input to a file on disk. Any
new targets should inherit :code:`streaming_form_data.targets.BaseTarget` and
define a :code:`data_received` function.

Usage
-----

.. code-block:: python

    >>> from streaming_form_data import StreamingFormDataParser
    >>> from streaming_form_data.targets import ValueTarget, FileTarget
    >>>
    >>> headers = {'Content-Type': 'multipart/form-data; boundary=boundary'}
    >>>
    >>> parser = StreamingFormDataParser(headers=headers)
    >>>
    >>> parser.register('name', ValueTarget())
    >>> parser.register('file', FileTarget('/tmp/file.txt'))
    >>>
    >>> parser.data_received(chunk)
