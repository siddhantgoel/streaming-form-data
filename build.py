from setuptools import Extension

try:
    from Cython.Build import cythonize
except ImportError:
    USE_CYTHON = False
else:
    USE_CYTHON = True


def build(setup_kwargs):
    file_ext = 'pyx' if USE_CYTHON else 'c'

    extensions = [
        Extension(
            'streaming_form_data._parser',
            ['streaming_form_data/_parser.{}'.format(file_ext)],
        )
    ]

    if USE_CYTHON:
        extensions = cythonize(extensions)

    setup_kwargs.update({'ext_modules': extensions})
