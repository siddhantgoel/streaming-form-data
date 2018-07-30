Streaming multipart/form-data parser
====================================

.. image:: https://travis-ci.org/siddhantgoel/streaming-form-data.svg?branch=stable
    :target: https://travis-ci.org/siddhantgoel/streaming-form-data

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data

.. image:: https://readthedocs.org/projects/streaming-form-data/badge/?version=latest
    :target: https://streaming-form-data.readthedocs.io/en/latest/


:code:`streaming_form_data` provides a Python parser for parsing
:code:`multipart/form-data` input chunks (the most commonly used encoding when
submitting data through HTML forms).

Chunk size is determined by the API user, but currently there are no
restrictions on what the chunk size should be, since the parser works
byte-by-byte (which means that passing the entire input as a single chunk should
also work).

The main entry point is the :code:`StreamingFormDataParser` class, which expects
a dictionary of request :code:`headers`.

The parser is fed chunks of (bytes) input, and takes action depending on what
the current byte is. In case it notices input that's expected (input that has
been registered by calling :code:`parser.register`, it will pass on the input to
the registered :code:`Target` class which will then decide what to do with it.
In case there's a part which is not needed, it can be associated to a
:code:`NullTarget` object and it will be discarded.

Currently the following :code:`Target` classes are included with this library.

- :code:`ValueTarget` - holds the input in memory
- :code:`FileTarget` - pipes the input to a file on disk
- :code:`SHA256Target` - computes the SHA-256 hash of the input
- :code:`NullTarget` - discards the input completely

Any new targets should inherit :code:`streaming_form_data.targets.BaseTarget`
and define an :code:`on_data_received` function.

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

Please make sure you have Python 3 and pipenv_ installed.

1. Git clone the repository -
   :code:`git clone https://github.com/siddhantgoel/streaming-form-data`

2. Install the packages required for development -
   :code:`pipenv install --dev`

3. That's basically it. You should now be able to run the test suite -
   :code:`py.test`.


Authors
-------

- Siddhant Goel <`@siddhantgoel`_>
- Sergey Kolomenkin <`@kolomenkin`_>


.. _@kolomenkin: https://github.com/kolomenkin
.. _@siddhantgoel: https://github.com/siddhantgoel
.. _pipenv: https://docs.pipenv.org/install/#installing-pipenv
