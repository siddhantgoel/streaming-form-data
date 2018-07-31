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
    version='1.1.0',
    description='Streaming parser for multipart/form-data',
    long_description=long_description,
    author='Siddhant Goel',
    author_email='me@sgoel.org',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=['streaming_form_data'],
    ext_modules=extensions,
    python_requires='>=3.4.0',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
