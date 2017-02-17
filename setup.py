from setuptools import find_packages, setup

from Cython.Build import cythonize


def readme():
    with open('README.rst') as f:
        return f.read()


setup(
    name='streaming_form_data',
    version='0.2.0',
    description=readme(),
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=find_packages(exclude=['examples', 'tests', 'utils']),
    include_package_data=True,
    ext_modules=cythonize('streaming_form_data/finder.pyx')
)
