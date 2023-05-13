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

Installation
------------

.. code-block:: bash

    $ pip install streaming_form_data

The core parser is written in :code:`Cython`, which is a superset of Python that
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
    >>> for chunk in request.body:
    ...     parser.data_received(chunk)
    ...
    >>>

Usage can broadly be split into three stages.

1. Initialization
~~~~~~~~~~~~~~~~~

The :code:`StreamingFormDataParser` class expects a dictionary of HTTP request
headers when being instantiated. These headers are used to determine the input
:code:`Content-Type` and a few other metadata.

2. Input Registration
~~~~~~~~~~~~~~~~~~~~~

HTML forms typically have multiple fields. For instance, a form could have a
text input field called :code:`name` and a file input field called
:code:`file`.

This needs to be communicated to the parser using the :code:`parser.register`
function. This function expects two arguments - the name of the input field, and
the associated :code:`Target` class (which determines how the input should be
handled).

For instance, if you want to store the contents of the :code:`name` field in an
in-memory variable, and the :code:`file` field in a file on disk, you can tell
this to the parser as follows.

.. code-block:: python

    >>> name_target = ValueTarget()
    >>> file_target = FileTarget('/tmp/file.dat')
    >>>
    >>> parser.register('name', name_target)
    >>> parser.register('file', file_target)

Registering multiple targets is also supported.

.. code-block:: python

    >>> name_target = ValueTarget()
    >>> sha256_target = SHA256Target()
    >>>
    >>> parser.register('file', name_target)
    >>> parser.register('file', sha256_target)

In this case, the contents of the :code:`file` field would be streamed to both
the :code:`ValueTarget` as well as the :code:`SHA256Target`.

3. Streaming data
~~~~~~~~~~~~~~~~~

At this stage the parser has everything it needs to be able to work. Depending
on what web framework you're using, just pass the actual HTTP request body to
the parser, either one chunk at a time or the complete thing at once.

.. code-block:: python

    >> chunk = read_next_chunk() # depends on your web framework of choice
    >>
    >> parser.data_received(chunk)


API
---

:code:`StreamingFormDataParser`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This class is the main entry point, and expects a dictionary of HTTP request
:code:`headers`. These headers are used to determine the input
:code:`Content-Type` and a few other metadata.

:code:`Target` classes
~~~~~~~~~~~~~~~~~~~~~~

When registering inputs with the parser, instances of subclasses of the
:code:`Target` class should be used. These target classes ultimately determine
what to do with the data.

:code:`ValueTarget`
```````````````````

:code:`ValueTarget` objects hold the input in memory.

.. code-block:: python

    >>> target = ValueTarget()

:code:`FileTarget`
``````````````````

:code:`FileTarget` objects stream the contents to a file on-disk.

.. code-block:: python

    >>> target = FileTarget('/tmp/file.txt')

:code:`DirectoryTarget`
```````````````````````

:code:`DirectoryTarget` objects stream the contents to a directory on-disk.

.. code-block:: python

    >>> target = DirectoryTarget('/tmp/uploads/')

:code:`SHA256Target`
````````````````````

:code:`SHA256Target` objects calculate a :code:`SHA256` hash of the given input,
and hold the result in memory.

.. code-block:: python

    >>> target = SHA256Target()

:code:`NullTarget`
``````````````````

:code:`NullTarget` objects discard the input completely.

.. code-block:: python

    >>> target = NullTarget()

:code:`S3Target`
````````````````

:code:`S3Target` objects stream the contents of a file to an S3 bucket.

.. code-block:: python

    >>> target = S3Target("s3://<bucket>/path/to/key", "wb")

Custom :code:`Target` classes
`````````````````````````````

It's possible to define custom targets for your specific use case by inheriting
the :code:`streaming_form_data.targets.BaseTarget` class and overriding the
:code:`on_data_received` function.

.. code-block:: python

    >>> from streaming_form_data.targets import BaseTarget
    >>>
    >>> class CustomTarget(BaseTarget):
    ...     def on_data_received(self, chunk):
    ...         do_something(chunk)

If the :code:`Content-Disposition` header included the :code:`filename`
directive, this value will be available as the :code:`self.multipart_filename`
attribute in :code:`Target` classes.

Similarly, if the :code:`Content-Type` header is available for the uploaded
files, this value will be available as the :code:`self.multipart_content_type`
attribute in :code:`Target` classes.

:code:`Validator` classes
~~~~~~~~~~~~~~~~~~~~~~~~~

:code:`Target` classes accept a :code:`validator` callable when being
instantiated. Every time :code:`data_received` is called with a given
:code:`chunk`, the target runs this :code:`chunk` through the given callable.

This is useful for performing certain validation tasks like making sure the
input size is not exceeding a certain value. This is shown in the following code
snippet.

.. code-block:: python

    >>> from streaming_form_data.targets import ValueTarget
    >>>
    >>> target = ValueTarget(validator=MaxSizeValidator(100))


Examples
--------

- :code:`Bottle` - https://git.io/vhCUy
- :code:`Flask` - https://git.io/fjPoA
- :code:`Tornado` - https://git.io/vhCUM

If you'd like to document usage with another web framework (which ideally
allows chunked HTTP reads), please open an issue or a pull request.


.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`search`
