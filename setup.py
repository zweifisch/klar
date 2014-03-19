# from distutils.core import setup
from setuptools import setup

setup(
    name='klar',
    version='0.0.5',
    url='https://github.com/zweifisch/klar',
    keywords='micro web framework restful',
    license='MIT',
    description='a micro web framework',
    long_description=open('README.md').read(),
    author='Feng Zhou',
    author_email='zf.pascal@gmail.com',
    packages=['klar'],
    install_requires=['jsonschema', 'biro'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP :: WSGI'
    ],
    # entry_points={
    #     'console_scripts': ['klar=klar:cli'],
    # },
)
