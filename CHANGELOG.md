# CHANGELOG

## v1.12.0
- Add `S3Target` for streaming files directly to S3 (thanks [@tokicnikolaus])

## v1.11.1
- Replace deprecated `cgi` module usage with `email` (thanks [@jasopolis])
- Add support for Python 3.11 (thanks [@jasopolis])
- Build using Cython 0.29.34

## v1.11.0
- Support Python 3.10
- Build using Cython 0.29.24

## v1.10.2
- Fix type annotation for Target objects (thanks [@Wouterkoorn])
- Fix constant name in Tornado example (thanks [@remram44])

## v1.10.1
- Handle the case when a user does not provide any file with `DirectoryTarget`
  (thanks [@ibrewster])
- Handle leading CRLF when needed (thanks [@mephi42])

## v1.10.0
- Add `DirectoryTarget` for streaming different input files to an on-disk
  directory (thanks [@NteRySin])

## v1.9.0
- Support Python 3.9
- Build using Cython 0.29.24

## v1.8.1
- Fix `Content-Type` header parsing bug (thanks [@raethlein])
- Build using Cython 0.29.21

## v1.8.0
- Build and publish binary wheels for Linux, macOS and Windows

## v1.7.1
- Fix build issues related to PEP 517

## v1.7.0
- Support Python 3.8
- Built using Cython 0.29.17

## v1.6.0
- Support registering multiple targets per same part
- Built using Cython 0.29.15

## v1.5.2
- Fix `pyproject.toml`

## v1.5.1
- Update README

## v1.5.0
- Make file `content_type` (from the `Content-Type` header) available as
  `self.multipart_content_type` attribute in `Target` classes
- Build using Cython 0.29.14

## v1.4.0
- Built using Cython 0.29.6

## v1.3.0
- Built using Cython 0.29.1

## v1.2.0
- Built using Cython 0.28.5
- Use `keys()` to iterate over request headers

## v1.1.0
- Built using Cython 0.28.4
- Improve documentation

## v1.0.0
- Add exception handling in the `_Parser` class (move to the
  `PS_ERROR` state when targets raise an exception)
- Support chunk-input validation in `Target` objects using `validator`
  callables
- Add function hooks in `Target` classes which should be overridden instead of
  the actual functions themselves (users should now define `on_data_received`
  instead of overriding `data_received`)

## v0.6.1
- Include `streaming_form_data/_parser.pyx` file in the distribution to avoid
  installation errors

## v0.6.0
- Major performance improvements; we're now able to parse ~1800MB per second,
  from ~15MB per second in the previous version (thanks [@kolomenkin])

## v0.5.1
- Fix parser bug which could lead to spurious CR or CRLF being added to the end
  of transferred form field value (thanks [@kolomenkin])

## v0.5.0
- Make `filename` (from the `Content-Disposition` header) available as
  `self.multipart_filename` attribute in `Target` classes (thanks [@kolomenkin])
- Add example usage for `bottle` framework (thanks [@kolomenkin])
- Refactor tests to work with random bytes instead of increasing repository size
  with test files (thanks [@kolomenkin])
- Make `Content-Type` header lookups truly case-insensitive (mixed cases also
  allowed) (thanks [@kolomenkin])

## v0.4.5
- Make `Content-Type` header lookups case-insensitive

## v0.4.4
- Performance: mark `active`, `found`, and `inactive`
  properties on `Finder` instances as `cpdef`-ed methods, decreasing
  the Python-space operations for an increase in speed
- Performance: remove `_Failed` exception and replace it with error codes,
  decreasing the Python-space operations for a speed increase
- Include `Cython`-generated annotation file to keep an eye on the
  Python-interaction level

## v0.4.3
- Performance: `cdef` declare `long` variable responsible for
  iterating over the buffer

## v0.4.2
- Performance: avoid repeated function calls to check the buffer length

## v0.4.1
- Add Sphinx documentation and make them available on
  https://streaming-form-data.readthedocs.org

## v0.4.0
- Provide `parser.register` function for handling uploaded parts,
  replacing the `expected_parts` argument
- Remove `Part` class from the user-facing API since it just makes the
  API look messy and verbose
- Update documentation

## v0.3.2
- Include upload form in tornado usage example
- Call `unset_active_part` when a delimiter string is found

## v0.3.1
- Update README and tornado usage example
- Adjust import paths for the `Part` class

## v0.3.0
- Initial release

[@NteRySin]: https://github.com/NteRySin
[@Wouterkoorn]: https://github.com/Wouterkoorn
[@ibrewster]: https://github.com/ibrewster
[@jasopolis]: https://github.com/jasopolis
[@kolomenkin]: https://github.com/kolomenkin
[@mephi42]: https://github.com/mephi42
[@raethlein]: https://github.com/raethlein
[@remram44]: https://github.com/remram44
[@tokicnikolaus]: https://github.com/tokicnikolaus
