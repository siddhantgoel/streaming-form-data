from setuptools import setup, Extension
import sys
import warnings


with open('README.rst') as f:
    description = f.read()


cythonize = None


try:
    sys.argv.remove('--using-cython')
except ValueError:
    pass
else:
    try:
        from Cython.Build import cythonize
    except ImportError:
        warnings.warn('Cython not installed')


if cythonize:
    extensions = cythonize('streaming_form_data/finder.pyx')
else:
    extensions = [Extension('streaming_form_data.finder',
                            ['streaming_form_data/finder.c'])]


setup(
    name='streaming_form_data',
    version='0.2.0',
    description=description,
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=['streaming_form_data'],
    ext_modules=extensions
)
