#!/usr/bin/python

from setuptools import setup, find_packages
import platform

import dexcom_reader

def readme():
    with open("README.md") as f:
        return f.read()

setup(name='dexcom_reader',
    version='0.0.7', # http://semver.org/
    description='Audit, and inspect data from Dexcom G4.',
    long_description=readme(),
    author="Will Nowak",
    # I'm just maintaining the package, @compbrain authored it.
    author_email="compbrain+dexcom_reader@gmail.com",
    maintainer="Ben West",
    maintainer_email="bewest+dexcom_reader@gmail.com",
    url="https://github.com/compbrain/dexcom_reader",
    packages=find_packages( ),
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
    package_data={
      'dexcom_reader': ['etc/udev/rules.d/*']
    },
    zip_safe=False,
    include_package_data=True
)

#####
# EOF
