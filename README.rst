Streaming multipart/form-data parser
====================================

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data

.. image:: https://travis-ci.org/siddhantgoel/streaming-form-data.svg?branch=master
    :target: https://travis-ci.org/siddhantgoel/streaming-form-data


:code:`streaming_form_data` provides a Python parser for parsing
multipart/form-data input chunks. Chunk size is determined by the API user, but
currently there are no restrictions on what the size should be, since the parser
works byte-by-byte. Although, this also means that passing the entire input as a
single chunk should also work.

The main entry point is the :code:`StreamingFormDataParser` class, which expects
a list of :code:`expected_parts`, and a dictionary of request :code:`headers`.
Each element in the :code:`expected_parts` list represents a single part of the
complete multipart input, and should be an instance of the :code:`Part` class.

The parser is fed chunks of (byte) input, and takes action depending on what the
current byte is. In case it notices input that's expected (determined by
:code:`expected_parts`), it passes on the input to :code:`Part.data_received`,
which in turn calls :code:`Target.data_received` with the input, which then
decides what to do with it. At any point of time, only one part of the
:code:`expected_parts` is active. In case there's a part that we don't need,
this input is simply discarded using a :code:`NullTarget` object.

Currently two targets are included with this library - :code:`ValueTarget` and
:code:`FileTarget`. :code:`ValueTarget` stores the input in memory, and
:code:`FileTarget` pipes the input to a file on disk. Any new targets should
inherit :code:`streaming_form_data.targets.BaseTarget` and define a
:code:`data_received` function.

This library is currently under development. There are quite a few tests in the
:code:`tests/` directory, but it hasn't been battle tested, hence production
usage is not recommended (yet).

Usage
-----

.. code-block:: python

    >>> from streaming_form_data.parser import StreamingFormDataParser
    >>> from streaming_form_data.part import Part
    >>> from streaming_form_data.targets import ValueTarget
    >>>
    >>> name = Part('name', ValueTarget())
    >>> file_ = Part('file', FileTarget('/tmp/file.txt'))
    >>>
    >>> headers = {'Content-Type': 'multipart/form-data; boundary=boundary'}
    >>> expected_parts = (name, file_)
    >>>
    >>> parser = StreamingFormDataParser(expected_parts=expected_parts, headers=headers)
    >>> parser.start()
    >>>
    >>> parser.data_received(chunk)
