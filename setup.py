#! /usr/bin/env python

"""Perform setup of the package for build."""
import glob
import io
import os
import re
import fnmatch

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

from setuptools import setup, find_packages

with io.open('eqllib/__init__.py', 'rt', encoding='utf8') as f:
    __version__ = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


def recursive_glob(root, pattern):
    for base, dirs, files in os.walk(os.path.join('eqllib', root)):
        matches = fnmatch.filter(files, pattern)
        for filename in matches:
            yield os.path.relpath(os.path.join(base, filename), 'eqllib')


setup(
    name='eqllib',
    version=__version__,
    description='EQL Analytics Library',
    install_requires=[
        "toml~=0.10.0",
        "eql==0.6.0",
        "jsl~=0.2",
        "jsonschema~=2.5",
    ],
    extras_require={
        'docs': {
            "sphinx",
            "sphinx_rtd_theme",
        }
    },
    entry_points={
        'console_scripts': [
            'eqllib=eqllib.main:normalize_main',
        ],
    },
    package_data={
        'eqllib': ['enterprise-attack.json'] +
                  list(recursive_glob('domains', '*.toml')) +
                  list(recursive_glob('analytics', '*.toml')) +
                  list(recursive_glob('sources', '*.toml')),
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
