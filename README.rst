Streaming multipart/form-data parser
====================================

.. image:: https://travis-ci.org/siddhantgoel/streaming-form-data.svg?branch=master
    :target: https://travis-ci.org/siddhantgoel/streaming-form-data

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data

.. image:: https://readthedocs.org/projects/streaming-form-data/badge/?version=latest
    :target: https://streaming-form-data.readthedocs.io/en/latest/


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

Please note, that this library has only been tested with Python 3 (specifically,
versions 3.3, 3.4, 3.5, and 3.6). Python 2.7 is not supported yet, but pull
requests are always welcome!

Installation
------------

.. code-block:: bash

    $ pip install streaming-form-data

In case you prefer cloning the Github repository and installing manually, please
note that :code:`master` is the development branch, so :code:`stable` is what
you should be cloning.

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

Development
-----------

To work on this package, please make sure you have a working Python 3
installation on your system.

1. Create a virtualenv -
   :code:`python -m venv venv && source venv/bin/activate`.

2. Git clone the repository -
   :code:`git clone https://github.com/siddhantgoel/streaming-form-data`

3. Install the packages required for development -
   :code:`pip install -r requirements.dev.txt`

4. Install this package - :code:`pip install .`.

5. You should now be able to run the test suite - :code:`py.test tests/`.
