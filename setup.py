#!/usr/bin/env python

import os
from unittest import TestLoader
from setuptools import setup

def tests():
    return TestLoader().discover('tests')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(BASE_DIR, 'README.rst')) as fp:
        README = fp.read()
except IOError:
    README = ''

setup(
    name='pygtkdrawingwindow',
    version='0.1.0',
    description='',
    long_description=README,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License'
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Multimedia :: Graphics',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Widget Sets'
    ],
    keywords='gtk',
    url='https://github.com/dead-beef/pygtkdrawingwindow',
    author='dead-beef',
    license='MIT',
    py_modules=['pygtkdrawingwindow'],
    test_suite='setup.tests',
    install_requires=['enum34'],
    extras_require={
        'dev': [
            'sphinx',
            'sphinx_rtd_theme',
            'twine>=1.8.1',
            'wheel'
        ]
    },
    include_package_data=True,
    zip_safe=False
)
