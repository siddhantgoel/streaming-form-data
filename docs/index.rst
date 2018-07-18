Streaming multipart/form-data parser
====================================

.. image:: https://travis-ci.org/siddhantgoel/streaming-form-data.svg?branch=stable
    :target: https://travis-ci.org/siddhantgoel/streaming-form-data

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data


:code:`streaming_form_data` provides a Python parser for parsing
:code:`multipart/form-data` input chunks (the most commonly used encoding when
submitting data through HTML forms).

Chunk size is determined by the API user, but currently there are no
restrictions on what the chunk size should be, since the parser works
byte-by-byte (which means that passing the entire input as a single chunk should
also work).

Please note, that this library has only been tested with Python 3 (specifically,
versions 3.3, 3.4, 3.5, and 3.6).

Installation
------------

.. code-block:: bash

    $ pip install streaming_form_data

The core parser is written in :code:`Cython`, which is a superset of Python but
compiles the input down to a C extension which can then be imported in normal
Python code.

The compiled C parser code is included in the PyPI package, hence the
installation requires a working C compiler.

Usage
-----

.. code-block:: python

    >>> from streaming_form_data import StreamingFormDataParser
    >>> from streaming_form_data.targets import ValueTarget, FileTarget, NullTarget
    >>>
    >>> headers = {'Content-Type': 'multipart/form-data; boundary=boundary'}
    >>>
    >>> parser = StreamingFormDataParser(headers=headers)
    >>>
    >>> parser.register('name', ValueTarget())
    >>> parser.register('file', FileTarget('/tmp/file.txt'))
    >>> parser.register('discard-me', NullTarget())
    >>>
    >>> parser.data_received(chunk)

The parser is fed chunks of (bytes) input, and takes action depending on what
the current byte is. In case it notices input that's expected (input that has
been registered by calling :code:`parser.register`, it will pass on the input to
the registered :code:`Target` class which will then decide what to do with it.
In case there's a part which is not needed, it can be associated to a
:code:`NullTarget` object and it will be discarded.

If the :code:`Content-Disposition` header included the :code:`filename`
directive, this value will be available as the :code:`self.multipart_filename`
attribute in :code:`Target` classes.


API
---

:code:`StreamingFormDataParser`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This class is the main entry point, and expects a dictionary of request
:code:`headers`. These headers are used to determine the input
:code:`Content-Type` and some other metadata.

:code:`Target` classes
~~~~~~~~~~~~~~~~~~~~~~

When registering inputs with the parser, instances of subclasses of the
:code:`Target` class should be used, since these targets ultimately determine
what to do with the data.

Currently the following :code:`Target` classes are included with this library.

- :code:`ValueTarget` - holds the input in memory
- :code:`FileTarget` - pipes the input to a file on disk
- :code:`SHA256Target` - computes the SHA-256 hash of the input
- :code:`NullTarget` - discards the input completely

Any new targets should inherit :code:`streaming_form_data.targets.BaseTarget`
and define an :code:`on_data_received` function.

:code:`Validator` classes
~~~~~~~~~~~~~~~~~~~~~~~~~

:code:`Target` classes accept a list of :code:`validator` callables when being
instantiated. Every time :code:`data_received` is called with a given
:code:`chunk`, the target runs this :code:`chunk` through all the callables in
the :code:`validators` it has.

This is useful for performing certain validation tasks like making sure the
input size is not exceeding a certain value. This is shown in the following code
snippet.

.. code-block:: python

    >>> from streaming_form_data import StreamingFormDataParser
    >>> from streaming_form_data.targets import ValueTarget
    >>> from streaming_form_data.validators import MaxSizeValidator
    >>>
    >>> headers = {'Content-Type': 'multipart/form-data; boundary=boundary'}
    >>>
    >>> parser = StreamingFormDataParser(headers=headers)
    >>>
    >>> parser.register('name', ValueTarget(validators=(MaxSizeValidator(100),)))
    >>>
    >>> parser.data_received(chunk)


Examples
--------

- :code:`Bottle` - https://git.io/vhCUy
- :code:`Tornado` - https://git.io/vhCUM

If you'd like to document usage with another web framework (which ideally
allows chunked HTTP reads), please open an issue or a pull request.


.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`search`
