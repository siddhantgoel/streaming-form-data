from setuptools import setup, Extension, find_packages
import sys


with open('README.rst') as f:
    long_description = f.read()


cythonize = None


try:
    from Cython.Build import cythonize
except ImportError:
    pass


if cythonize:
    extensions = cythonize('streaming_form_data/core/finder.pyx')
else:
    extensions = [Extension('streaming_form_data.core.finder',
                            ['streaming_form_data/core/finder.c'])]


setup(
    name='streaming_form_data',
    version='0.2.0',
    description='Streaming parser for multipart/form-data',
    long_description=long_description,
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=find_packages(exclude=['examples', 'tests', 'utils']),
    ext_modules=extensions
)
