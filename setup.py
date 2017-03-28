from setuptools import setup, find_packages


with open('README.rst') as f:
    long_description = f.read()


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
)
