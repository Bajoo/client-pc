#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand
import sys


# Load the __version__ variable
exec(open('bajoo/__version__.py').read())


with open('README.rst') as readme_file:
    long_description = readme_file.read()


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = ''

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex
        errno = tox.cmdline(args=shlex.split(self.tox_args))
        sys.exit(errno)


setup(
    name="bajoo",
    version=__version__,  # noqa
    description="Official client for the cloud storage service Bajoo",
    long_description=long_description,
    url="https://www.bajoo.fr",
    author="Bajoo",
    author_email="support@bajoo.fr",
    license="GPLv3",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Communications :: File Sharing"
    ],
    keywords="bajoo storage cloud file-sharing",
    packages=find_packages(),
    install_requires=[],
    tests_require=['tox'],
    include_package_data=True,
    package_data={},
    entry_points={
        "console_scripts": [
            "bajoo=bajoo:main"
        ]
    },
    cmdclass={
        'test': Tox
    },
    zip_safe=True
)
