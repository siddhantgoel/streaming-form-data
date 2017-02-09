from setuptools import find_packages, setup
import subprocess


def readme():
    with open('README.md') as f:
        return f.read()
    return output.decode('utf-8').strip()


setup(
    name='streaming_form_data',
    version='0.0.1',
    description=readme(),
    author='Siddhant Goel',
    packages=find_packages(exclude=['data', 'examples', 'tests', 'utils']),
    include_package_data=True
)
