from setuptools import setup, Extension


with open('README.rst') as f:
    description = f.read()


setup(
    name='streaming_form_data',
    version='0.2.0',
    description=description,
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=['streaming_form_data'],
    ext_modules=[Extension('streaming_form_data.finder',
                           ['streaming_form_data/finder.c'])]
)
