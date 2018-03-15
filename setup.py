#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os import path
from setuptools import setup
from distutils.cmd import Command

NAME = 'redmab'

ROOTDIR = path.abspath(os.path.dirname(__file__))

with open(os.path.join(ROOTDIR, 'README.rst')) as f:
    readme = f.read()

with open(os.path.join(ROOTDIR, 'docs', 'release-notes.rst')) as f:
    history = f.read()

with open(os.path.join(ROOTDIR, NAME, 'VERSION')) as f:
    version = str(f.read().strip())


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        import subprocess

        raise SystemExit(
            subprocess.call([sys.executable, '-m', 'test']))


cmdclass = {'test': TestCommand}
ext_modules = []

setup(
    name=NAME,
    version=version,
    description='Multi-Armed Bandit implementation in redis',
    author='John Loehrer',
    author_email='72squared@gmail.com',
    url='https://github.com/72squared/%s' % NAME,
    download_url='https://github.com/72squared/%s/archive/%s.tar.gz' %
                 (NAME, version),
    keywords='redis multi-armed bandit',
    packages=[NAME],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Environment :: Web Environment',
        'Operating System :: POSIX'],
    license='MIT',
    install_requires=['redpipe>=2.0.0'],
    tests_require=['redislite>=3.0.271', 'tox', 'coverage'],
    include_package_data=True,
    long_description=readme + '\n\n' + history,
    cmdclass=cmdclass,
    ext_modules=ext_modules
)
