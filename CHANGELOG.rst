CHANGELOG
=========

v1.6.0
------
- Support registering multiple targets per same part
- Built using Cython 0.29.15

v1.5.2
------
- Fix :code:`pyproject.toml`

v1.5.1
------
- Update README

v1.5.0
------
- Make file :code:`content_type` (from the :code:`Content-Type` header) available
  as :code:`self.multipart_content_type` attribute in :code:`Target` classes
- Build using Cython 0.29.14

v1.4.0
------
- Built using Cython 0.29.6

v1.3.0
------
- Built using Cython 0.29.1

v1.2.0
------
- Built using Cython 0.28.5
- Use :code:`keys()` to iterate over request headers

v1.1.0
------
- Built using Cython 0.28.4
- Improve documentation

v1.0.0
------
- Add exception handling in the :code:`_Parser` class (move to the
  :code:`PS_ERROR` state when targets raise an exception)
- Support chunk-input validation in :code:`Target` objects using
  :code:`validator` callables
- Add function hooks in :code:`Target` classes which should be overridden
  instead of the actual functions themselves (users should now define
  :code:`on_data_received` instead of overriding :code:`data_received`)

v0.6.1
------
- Include :code:`streaming_form_data/_parser.pyx` file in the distribution to avoid installation errors

v0.6.0
------
- Major performance improvements; we're now able to parse ~1800MB per second, from ~15MB per second in the previous version (thanks `@kolomenkin`_)

v0.5.1
------
- Fix parser bug which could lead to spurious CR or CRLF being added to the end
  of transferred form field value (thanks `@kolomenkin`_)

v0.5.0
------
- Make :code:`filename` (from the :code:`Content-Disposition` header) available
  as the :code:`self.multipart_filename` attribute in :code:`Target` classes
  (thanks `@kolomenkin`_)
- Add example usage for :code:`bottle` framework (thanks `@kolomenkin`_)
- Refactor tests to work with random bytes instead of increasing repository size
  with test files (thanks `@kolomenkin`_)
- Make :code:`Content-Type` header lookups truly case-insensitive (mixed cases
  also allowed) (thanks `@kolomenkin`_)

v0.4.5
------
- Make :code:`Content-Type` header lookups case-insensitive

v0.4.4
------

- Performance: mark :code:`active`, :code:`found`, and :code:`inactive`
  properties on :code:`Finder` instances as :code:`cpdef`-ed methods, decreasing
  the Python-space operations for an increase in speed
- Performance: remove :code:`_Failed` exception and replace it with error codes,
  decreasing the Python-space operations for a speed increase
- Include :code:`Cython`-generated annotation file to keep an eye on the
  Python-interaction level

v0.4.3
------

- Performance: :code:`cdef` declare :code:`long` variable responsible for
  iterating over the buffer

v0.4.2
------

- Performance: avoid repeated function calls to check the buffer length

v0.4.1
------

- Add Sphinx documentation and make them available on
  https://streaming-form-data.readthedocs.org

v0.4.0
------

- Provide :code:`parser.register` function for handling uploaded parts,
  replacing the :code:`expected_parts` argument
- Remove :code:`Part` class from the user-facing API since it just makes the
  API look messy and verbose
- Update documentation

v0.3.2
------

- Include upload form in tornado usage example
- Call :code:`unset_active_part` when a delimiter string is found

v0.3.1
------

- Update README and tornado usage example
- Adjust import paths for the :code:`Part` class

v0.3.0
------

- Initial release


.. _@kolomenkin: https://github.com/kolomenkin
