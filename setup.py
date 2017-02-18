from setuptools import setup, Extension
import sys


with open('README.rst') as f:
    description = f.read()


using_cython = False

cythonize = None


try:
    sys.argv.remove('--using-cython')
except ValueError:
    using_cython = False
else:
    try:
        from Cython.Build import cythonize
    except ImportError:
        using_cython = False
    else:
        using_cython = True


if using_cython:
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
