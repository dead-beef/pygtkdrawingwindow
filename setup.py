from unittest import TestLoader
from setuptools import setup

def tests():
    return TestLoader().discover('tests')

setup(name='pygtkdrawingwindow',
      version='0.1',
      description='',
      long_description='',
      classifiers=[
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'License :: OSI Approved :: MIT License'
      ],
      keywords='',
      url='https://github.com/dead-beef/pygtkdrawingwindow',
      author='dead-beef',
      author_email='contact@dead-beef.tk',
      license='MIT',
      py_modules=['pygtkdrawingwindow'],
      data_files=[
          ('share/pygtkdrawingwindow',
           ['README.md', 'LICENSE', 'demo.py'])
      ],
      test_suite='setup.tests',
      install_requires=[],
      include_package_data=True,
      zip_safe=False)
