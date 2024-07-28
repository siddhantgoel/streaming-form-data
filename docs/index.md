# streaming-form-data

[![image](https://img.shields.io/pypi/v/streaming-form-data.svg)](https://pypi.python.org/pypi/streaming-form-data)

`streaming_form_data` provides a Python parser for parsing `multipart/form-data` input
chunks (the most commonly used encoding when submitting data through HTML forms).

Chunk size is determined by the API user, but currently there are no
restrictions on what the chunk size should be, since the parser works
byte-by-byte (which means that passing the entire input as a single chunk should
also work).

## Installation

```
$ pip install streaming_form_data
```

The core parser is written in `Cython`, which is a superset of Python that compiles the
input down to a C extension which can then be imported in normal Python code.

The compiled C parser code is included in the PyPI package, hence the
installation requires a working C compiler.

## Usage

```python
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
```

Usage can broadly be split into three stages.

### 1. Initialization

The `StreamingFormDataParser` class expects a dictionary of HTTP request headers when
being instantiated. These headers are used to determine the input `Content-Type` and a
few other metadata.

Optionally, you can enable strict mode in the parser by setting the `strict` keyword
argument to `True`. In strict mode, the parser throws `UnexpectedPartException` if it
starts to parse a field whose name has not been registered. When not in strict mode,
unexpected parts are silently ignored.

### 2. Input Registration

HTML forms typically have multiple fields. For instance, a form could have a text input
field called `name` and a file input field called `file`.

This needs to be communicated to the parser using the `parser.register` function. This
function expects two arguments - the name of the input field, and the associated
`Target` class (which determines how the input should be handled).

For instance, if you want to store the contents of the `name` field in an in-memory
variable, and the `file` field in a file on disk, you can tell this to the parser as
follows.

```python
>>> name_target = ValueTarget()
>>> file_target = FileTarget('/tmp/file.dat')
>>>
>>> parser.register('name', name_target)
>>> parser.register('file', file_target)
```

Registering multiple targets is also supported.

```python
>>> name_target = ValueTarget()
>>> sha256_target = SHA256Target()
>>>
>>> parser.register('file', name_target)
>>> parser.register('file', sha256_target)
```

In this case, the contents of the `file` field would be streamed to both the
`ValueTarget` as well as the `SHA256Target`.

### 3. Streaming data

At this stage the parser has everything it needs to be able to work. Depending
on what web framework you're using, just pass the actual HTTP request body to
the parser, either one chunk at a time or the complete thing at once.

```python
>> chunk = read_next_chunk() # depends on your web framework of choice
>>
>> parser.data_received(chunk)
```

## API

### `StreamingFormDataParser`

This class is the main entry point. It expects a dictionary of HTTP request `headers`
and has a keyword argument `strict`. The headers are used to determine the input
`Content-Type` and a few other metadata. The strict flag is used to enable or disable
the strict mode.

### `Target` classes

When registering inputs with the parser, instances of subclasses of the `Target` class
should be used. These target classes ultimately determine what to do with the data.

#### `ValueTarget`

`ValueTarget` objects hold the input in memory.

```python
>>> target = ValueTarget()
```

#### `FileTarget`

`FileTarget` objects stream the contents to a file on-disk.

```python
>>> target = FileTarget('/tmp/file.txt')
```

#### `DirectoryTarget`

`DirectoryTarget` objects stream the contents to a directory on-disk.

```python
>>> target = DirectoryTarget('/tmp/uploads/')
```

#### `SHA256Target`

`SHA256Target` objects calculate a `SHA256` hash of the given input, and hold the result
in memory.

```python
>>> target = SHA256Target()
```

#### `NullTarget`

`NullTarget` objects discard the input completely.

```python
>>> target = NullTarget()
```

#### `S3Target`

`S3Target` objects stream the contents of a file to an S3 bucket.

```python
>>> target = S3Target("s3://<bucket>/path/to/key", "wb")
```

#### `CSVTarget`

`CSVTarget` objects process and release CSV lines in chunks.

```python
>>> target = CSVTarget()
```

#### `ListTarget`

`ListTarget` objects store the input in an in-memory list of bytes.

```python
>>> target = ListTarget()
```

#### Custom `Target` classes

It's possible to define custom targets for your specific use case by inheriting the
`streaming_form_data.targets.BaseTarget` class and overriding the `on_data_received`
function.

```python
>>> from streaming_form_data.targets import BaseTarget
>>>
>>> class CustomTarget(BaseTarget):
...     def on_data_received(self, chunk):
...         do_something(chunk)
```

If the `Content-Disposition` header included the `filename` directive, this value will
be available as the `self.multipart_filename` attribute in `Target` classes.

Similarly, if the `Content-Type` header is available for the uploaded files, this value
will be available as the `self.multipart_content_type` attribute in `Target` classes.

### `Validator` classes

`Target` classes accept a `validator` callable when being instantiated. Every time
`data_received` is called with a given `chunk`, the target runs this `chunk` through the
given callable.

This is useful for performing certain validation tasks like making sure the input size
is not exceeding a certain value. This is shown in the following code snippet.

```python
>>> from streaming_form_data.targets import ValueTarget
>>>
>>> target = ValueTarget(validator=MaxSizeValidator(100))
```

### Exceptions

#### `ParseFailedException`

This exception is the base class of the `streaming_form_data` exceptions. It can be
raised during initialization, registering parts or reading chunks.

#### `UnexpectedPartException`

This exception is raised when the parser is in strict mode and starts to parse an
unexpected part. It contains `part_name` attribute to check the name of the unexpected
part. In can only be raised from `data_received`.

```python
>>> try:
>>>    parser.data_received(chunk)
>>> except streaming_form_data.parser.UnexpectedPartException as e:
>>>    print(e.part_name)
>>>    raise
```

## Examples

- `Bottle` - https://git.io/vhCUy
- `Flask` - https://git.io/fjPoA
- `Tornado` - https://git.io/vhCUM

If you'd like to document usage with another web framework (which ideally
allows chunked HTTP reads), please open an issue or a pull request.
