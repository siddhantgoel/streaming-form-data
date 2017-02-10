# Streaming multipart/form-data parser

`streaming_form_data` provides a Python parser for parsing multipart/form-data input chunks. Passing the entire input should also work, when passed as a single chunk. But the use case here is to have the parser parse the values in chunks (of a size determined by the user of the API).

The main entry point is the `StreamingFormDataParser`, which expects a list of `expected_parts` (each part should be an instance of the `Part` class, and represents a single part of the complete multipart input), and a dictionary of request headers.

This library is currently under development. There are some tests in the `tests/` directory, but they don't test the real corner cases yet, hence usage is not recommended.

## Usage

```python
>>> from streaming_form_data.parser import StreamingFormDataParser
>>> from streaming_form_data.part import Part
>>> from streaming_form_data.targets import ValueTarget
>>> part = Part('name', ValueTarget())
>>> parser = StreamingFormDataParser(expected_parts=(part,), headers={'Content-Type': 'multipart/form-data; boundary=boundary'})
>>> parser.data_received(chunk)
```
