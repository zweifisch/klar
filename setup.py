# from distutils.core import setup
from setuptools import setup

setup(
    name='klar',
    version='0.0.0',
    description='a micro web framework',
    author='Feng Zhou',
    author_email='zf.pascal@gmail.com',
    packages=['klar'],
    install_requires=['jsonschema'],
    # entry_points={
    #     'console_scripts': ['klar=klar:cli'],
    # },
)
