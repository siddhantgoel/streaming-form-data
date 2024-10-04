# Streaming multipart/form-data parser

[![image](https://github.com/siddhantgoel/streaming-form-data/actions/workflows/test.yml/badge.svg)](https://github.com/siddhantgoel/streaming-form-data/actions/workflows/test.yml) [![image](https://github.com/siddhantgoel/streaming-form-data/actions/workflows/build.yml/badge.svg)](https://github.com/siddhantgoel/streaming-form-data/actions/workflows/build.yml)
[![image](https://img.shields.io/pypi/v/streaming-form-data.svg)](https://pypi.python.org/pypi/streaming-form-data)
[![image](https://img.shields.io/pypi/pyversions/streaming-form-data.svg)](https://pypi.python.org/pypi/streaming-form-data)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

`streaming_form_data` provides a Python parser for parsing `multipart/form-data`
input chunks (the encoding used when submitting data over HTTP through HTML
forms).

## Testimonials

> [_this speeds up file uploads to my Flask app by **more than factor 10**_](https://github.com/pallets/werkzeug/issues/875#issuecomment-429287766)

> [_Thanks a lot for your fix with streaming-form-data. I can finally upload gigabyte sized files at good speed and without memory filling up!_](https://github.com/pallets/werkzeug/issues/875#issuecomment-530020990)

> [_huge thanks to @siddhantgoel with his "streaming-form-data" that saves me from the slow file reads I get with @FastAPI!_](https://twitter.com/bebenzrr/status/1654952147132248064)

## Installation

```bash
$ pip install streaming-form-data
```

In case you prefer cloning the Github repository and installing manually, please
note that `main` is the development branch, so `stable` is what you should be
working with.

## Usage

```python
>>> from streaming_form_data import StreamingFormDataParser
>>> from streaming_form_data.targets import FileTarget, NullTarget, GCSTarget, S3Target, ValueTarget
>>>
>>> headers = {"Content-Type": "multipart/form-data; boundary=boundary"}
>>>
>>> parser = StreamingFormDataParser(headers=headers)
>>>
>>> parser.register("name", ValueTarget())
>>> parser.register("file-local", FileTarget("/path/to/file.txt"))
>>> parser.register("file-s3", S3Target("s3://bucket/path/to/key"))
>>> parser.register("file-gcs", GCSTarget("gs://bucket/path/to/key"))
>>> parser.register("discard-me", NullTarget())
>>>
>>> for chunk in request.body:
...     parser.data_received(chunk)
...
>>>
```

## Documentation

Up-to-date documentation is available on [Read the Docs].

## Development

Please make sure you have Python 3.9+ and [pip-tools] installed.

Since this package includes a C extension, please make sure you have a working C
compiler available. On Debian-based distros this usually means installing the
`build-essentials` package.

1. Git clone the repository:
   `git clone https://github.com/siddhantgoel/streaming-form-data`

2. Install the packages required for development:
   `make pip-sync`

3. Install `streaming_form_data` itself:
   `pip install .`

4. That's basically it. You should now be able to run the test suite:
   `make test`

Note that if you make any changes to Cython files (`.pyx, .pxd, .pxi`), you'll need to re-compile (`make compile`) and re-install `streaming_form_data` before you can test your changes.

[pip-tools]: https://pypi.org/project/pip-tools/
[Read the Docs]: https://streaming-form-data.readthedocs.io/
