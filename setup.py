#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.cmd import Command
from distutils.command.build import build as BuildCommand
from glob import glob
import os
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as InstallCommand
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


class Build(BuildCommand):
    sub_commands = [('build_translation', None)] + BuildCommand.sub_commands


class BuildTranslation(Command):
    description = "Convert .po files into .mo files."

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from pythongettext.msgfmt import Msgfmt

        locale_dir = os.path.join(os.path.dirname(__file__), 'bajoo/locale/')
        for src in glob(os.path.join(locale_dir, '*/LC_MESSAGES/*.po')):
            dest = src[:-2] + 'mo'
            with open(src, 'rb') as po_file, open(dest, 'wb') as mo_file:
                mo_file.write(Msgfmt(po_file).get())


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


setup_kwargs = {
    'name': "bajoo",
    'version': __version__,  # noqa
    'description': "Official client for the cloud storage service Bajoo",
    'long_description': long_description,
    'url': "https://www.bajoo.fr",
    'author': "Bajoo",
    'author_email': "support@bajoo.fr",
    'license': "GPLv3",
    'classifiers': [
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
    'keywords': "bajoo storage cloud file-sharing",
    'packages': find_packages(),
    'setup_requires': ['python-gettext'],
    'install_requires': [
        'appdirs==1.4',
        'requests>=2.6.0',
        'futures>=2.2.0',
        'python-gnupg',
        'watchdog',
        'pysocks'
    ],
    'tests_require': ['tox'],
    'include_package_data': True,
    'package_data': {
        # Note: esky build doesn't support 'include_package_data'
        'bajoo': ['locale/*/LC_MESSAGES/*.mo', 'assets/*/*.png']
    },
    'dependency_links': ['http://wxpython.org/Phoenix/snapshot-builds/'],
    'entry_points': {
        "console_scripts": [
            "bajoo=bajoo:main"
        ]
    },
    'cmdclass': {
        'install': Install,
        'test': Tox,
        'build': Build,
        'build_translation': BuildTranslation
    },
    'zip_safe': False,
    'options': {
        'bdist_esky': {
            'freezer_module': 'py2exe',
            'freezer_options': {
                'dll_excludes': {
                    # Note that users will have to install
                    # VCRedist 2008 by themselves.
                    'msvcp90.dll'
                },
                'skip_archive': True
            }
        },

    }
}


if sys.version_info[0] is 3:  # Python3 only
    setup_kwargs['install_requires'] += [
        'wxpython>=Phoenix-3.0.0.dev,<Phoenix-9999',
        'py2exe'
    ]

if sys.platform not in ['win32', 'cygwin', 'win64']:
    setup_kwargs['install_requires'] += [
        'notify2'
    ]


try:
    from esky import bdist_esky
except ImportError:
    print("Warning: esky package not found. It is needed to build the "
          "distributable archives.")
else:
    if sys.platform in ['win32', 'cygwin', 'win64']:

        if sys.version_info[0] is 2:  # Python 2
            try:
                import py2exe  # noqa
            except ImportError:
                print('Warning: To use esky, py2exe must be installed manually'
                      ' using this command:')
                print('\tpip install http://sourceforge.net/projects/py2exe/'
                      'files/latest/download?source=files')

        icon_path = './bajoo/assets/icons/bajoo.ico'
        setup_kwargs['scripts'] = [
            bdist_esky.Executable('start.py', name='Bajoo', gui_only=True,
                                  icon=icon_path)
        ]


setup(**setup_kwargs)
