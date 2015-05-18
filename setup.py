#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as InstallCommand
import sys


# Load the __version__ variable
exec(open('bajoo/__version__.py').read())


with open('README.rst') as readme_file:
    long_description = readme_file.read()


requirements = [
    'requests>=2.6.0',
    'futures>=2.2.0'
]
if sys.version_info[0] is 3:  # Python3 only
    requirements += [
        'wxpython>=Phoenix-3.0.0.dev,<Phoenix-9999'
    ]


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


class Install(InstallCommand):
    """Overrides the install command to check the presence of wxPython."""

    def run(self):
        # Note(Kevin): On Python 2, Bajoo should uses the stable 'Classic'
        # version. This version must be installed manually by the user
        # (usually the package manager of the distribution).
        # On python 3, Bajoo uses the 'Phoenix' version of wxPython.
        # At this time, the Phoenix version is not stable yet, and only daily
        # snapshots are available.

        if sys.version_info[0] is 2:
            try:
                import wx  # noqa
            except ImportError:
                print("""\
Bajoo depends on the library wxPython. This library is not available in the
Python Package Index (pypi), and so can't be automatically installed.
On Linux, you can install it from your distribution's package repositories.
On Windows, you can download it from http://wxpython.org/download.php""")
                raise Exception('wxPython not found.')
        InstallCommand.run(self)


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
    install_requires=requirements,
    tests_require=['tox'],
    include_package_data=True,
    package_data={},
    dependency_links=['http://wxpython.org/Phoenix/snapshot-builds/'],
    entry_points={
        "console_scripts": [
            "bajoo=bajoo:main"
        ]
    },
    cmdclass={
        'install': Install,
        'test': Tox
    },
    zip_safe=True
)
