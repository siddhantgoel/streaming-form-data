from setuptools import find_packages, setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='streaming_form_data',
    version='0.1.1',
    description=readme(),
    author='Siddhant Goel',
    author_email='siddhantgoel@gmail.com',
    license='MIT',
    url='https://github.com/siddhantgoel/streaming-form-data',
    packages=find_packages(exclude=['data', 'examples', 'tests', 'utils']),
    include_package_data=True
)
