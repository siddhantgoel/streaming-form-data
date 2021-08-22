from setuptools import Extension, find_packages, setup
import pathlib


here = pathlib.Path(__file__).parent.resolve()


with open(here.joinpath('README.md')) as fd:
    long_description = fd.read()


setup(
    name='streaming-form-data',
    version='1.10.0',
    description='Streaming parser for multipart/form-data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    ext_modules=[
        Extension(
            'streaming_form_data._parser', ['streaming_form_data/_parser.c'],
        )
    ],
    url='https://github.com/siddhantgoel/streaming-form-data',
    author='Siddhant Goel',
    author_email='me@sgoel.dev',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
        'Programming Language :: Cython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='form-data, forms, http, multipart, web',
    python_requires='>=3.6',
)
