#! /usr/bin/env python

"""Perform setup of the package for build."""
import io
import os
import re
import sys

from setuptools import Command
from setuptools.command.test import test as TestCommand

from setuptools import setup, find_packages

with io.open('eqllib/__init__.py', 'rt', encoding='utf8') as f:
    __version__ = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)


# Load utility functions directory for recursive globbing
with io.open('eqllib/utils.py', 'rt', encoding='utf8') as f:
    exec(f.read())


class Lint(Command):
    """Wrapper for the standard linters."""

    description = 'Lint the code'
    user_options = []

    def initialize_options(self):
        """Initialize options."""

    def finalize_options(self):
        """Finalize options."""

    def run(self):
        """Run the flake8 linter."""
        self.distribution.fetch_build_eggs(test_requires)
        self.distribution.packages.append('tests')

        from flake8.main import Flake8Command
        flake8cmd = Flake8Command(self.distribution)
        flake8cmd.options_dict = {}
        flake8cmd.run()


class Test(TestCommand):
    """Use pytest (http://pytest.org/latest/) in place of the standard unittest library."""

    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        """Need to ensure pytest_args exists."""
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def run_tests(self):
        """Run pytest."""
        import pytest
        sys.exit(pytest.main(self.pytest_args))


def relative_glob(root, pattern):
    for path in recursive_glob(root, pattern):  # noqa: F821
        yield os.path.relpath(os.path.join(path), 'eqllib')


extra_files = ['enterprise-attack.json.gz']
extra_files.extend(relative_glob('domains', '*.toml'))
extra_files.extend(relative_glob('analytics', '*.toml'))
extra_files.extend(relative_glob('sources', '*.toml'))

install_requires = [
    "toml~=0.9",
    "eql~=0.9.2",
    "jsl~=0.2",
    "jsonschema==2.6.0",
]

test_requires = [
    "pytest~=3.8.2",
    "pytest-cov==2.4",
    "flake8==2.5.1",
]

setup(
    name='eqllib',
    version=__version__,
    description='EQL Analytics Library',
    install_requires=install_requires,
    cmdclass={
        'lint': Lint,
        'test': Test
    },
    extras_require={
        'docs': [
            "sphinx==1.7.9",
            "sphinx_rtd_theme",
        ],
        'test': test_requires
    },
    entry_points={
        'console_scripts': [
            'eqllib=eqllib.main:normalize_main',
        ],
    },
    package_data={
        'eqllib': extra_files,
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
