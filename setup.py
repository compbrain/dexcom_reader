#!/usr/bin/python

from setuptools import setup, find_packages
import platform
import subprocess

def is_virtualenv ( ):
  import os
  proc = subprocess.Popen(['which', 'virtualenvwrapper'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  has_venv = proc.poll( ) == 0
  return os.environ.get('VIRTUAL_ENV', has_venv)

import dexcom_reader
def readme():
    with open("README.md") as f:
        return f.read()

dataFiles = [ ]
if platform.system( ) == 'Linux':
  prefix = '/'
  dataFiles = [
      (prefix + 'etc/udev/rules.d', ['etc/udev/rules.d/80-dexcom.rules']),
    ]
  if is_virtualenv( ):
    prefix = ''
    dataFiles = [ ]

setup(name='dexcom_reader',
    version='0.0.6', # http://semver.org/
    description='Audit, and inspect data from Dexcom G4.',
    long_description=readme(),
    author="Will Nowak",
    # I'm just maintaining the package, @compbrain authored it.
    # I don't have their email.
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
    data_files=dataFiles,
    zip_safe=False,
    include_package_data=True
)

#####
# EOF
