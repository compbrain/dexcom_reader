#!/usr/bin/python

from setuptools import setup, find_packages

import dexcom_reader
def readme():
    with open("README.md") as f:
        return f.read()

setup(name='dexcom_reader',
    version='0.0.1', # http://semver.org/
    description='Audit, and inspect data from Dexcom G4.',
    long_description=readme(),
    author="Medevice contributors",
    # I'm just maintaining the package, compbrain authored it.
    author_email="bewest+insulaudit@gmail.com",
    url="https://github.com/compbrain/dexcom_reader",
    packages=['dexcom_reader'],
    install_requires = [
      'pyserial'
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries'
    ],
    zip_safe=False,
)

#####
# EOF
