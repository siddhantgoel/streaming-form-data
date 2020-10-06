Streaming multipart/form-data parser
====================================

.. image:: https://github.com/siddhantgoel/streaming-form-data/workflows/streaming-form-data/badge.svg
    :target: https://github.com/siddhantgoel/streaming-form-data/workflows/streaming-form-data/badge.svg

.. image:: https://badge.fury.io/py/streaming-form-data.svg
    :target: https://pypi.python.org/pypi/streaming-form-data

.. image:: https://readthedocs.org/projects/streaming-form-data/badge/?version=latest
    :target: https://streaming-form-data.readthedocs.io/en/latest/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


:code:`streaming_form_data` provides a Python parser for parsing
:code:`multipart/form-data` input chunks (the most commonly used encoding when
submitting data over HTTP through HTML forms).

Installation
------------

.. code-block:: bash

    $ pip install streaming-form-data

In case you prefer cloning the Github repository and installing manually, please
note that :code:`master` is the development branch, so :code:`stable` is what
you should be working with.

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

Documentation
-------------

Up-to-date documentation is available on `Read the Docs`_.

Development
-----------

Please make sure you have Python 3.6+ and `pip-tools`_ installed. Additionally,
this package includes a C extension, so please make sure you have a working C
compiler available. On Debian-based distros this means installing the
:code:`build-essentials` package.

1. Git clone the repository -
   :code:`git clone https://github.com/siddhantgoel/streaming-form-data`

2. Install the packages required for development -
   :code:`pip install -r requirements-dev.txt`

3. That's basically it. You should now be able to run the test suite -
   :code:`make test`.

Please note that :code:`tests/test_parser_stress.py` stress tests the parser
with large inputs, which can take a while. As an alternative, pass the filename
as an argument to :code:`py.test` to run tests selectively.


.. _pip-tools: https://pypi.org/project/pip-tools/
.. _Read the Docs: https://streaming-form-data.readthedocs.io/
