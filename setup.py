from setuptools import setup, Extension


cythonize = None

try:
    from Cython.Build import cythonize
except ImportError:
    pass

if cythonize:
    extensions = cythonize('streaming_form_data/_parser.pyx')
else:
    extensions = [Extension('streaming_form_data._parser',
                            ['streaming_form_data/_parser.c'])]


with open('README.rst') as f:
    long_description = f.read()


setup(
    name='streaming_form_data',
    version='0.5.0',
    description='Streaming parser for multipart/form-data',
    long_description=long_description,
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=['streaming_form_data'],
    ext_modules=extensions
)
