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

        # About wxVersion:
        # Some systems allowed several version of wxPython to be installed
        # wxVersion allows to pick a version.
        # If wxVersion is not available, either wxPython is not installed,
        # either the system only allows only one version of wxPython.

        if not self.force and sys.version_info[0] is 2:
            try:
                import wxversion
                try:
                    wxversion.select(['3.0', '2.9', '2.8'])
                except wxversion.VersionError:
                    pass
            except ImportError:
                pass

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
    'description': "Bajoo storage client",
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
        'requests[security]>=2.6.0',
        'futures>=2.2.0',
        'watchdog>=0.8.3',
        'pysocks>=1.5.6',
        'pyasn1>=0.1.9',
        'ndg-httpsclient>=0.4.0'
    ],
    'tests_require': ['tox'],
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
    'data_files': []
}

# ############################################################################
# ### UNIX/LINUX #############################################################
# ############################################################################

setup_kwargs['include_package_data'] = True
if sys.platform not in ['win32', 'cygwin', 'win64', 'darwin']:
    setup_kwargs['install_requires'] += [
        'notify2>=0.3'
    ]

    if sys.platform.startswith('linux'):
        setup_kwargs['data_files'].extend([
            ('share/applications', ['bajoo/assets/bajoo.desktop']),
            ('share/bajoo/assets/images', glob('bajoo/assets/images/*.png')),
            ('share/bajoo/assets/images/container_status',
             glob('bajoo/assets/images/container_status/*.png')),
            ('share/bajoo/assets/images/trayicon_status',
             glob('bajoo/assets/images/trayicon_status/*.png')),
            ('share/bajoo/assets', ['bajoo/assets/exe_icon.ico',
                                    'bajoo/assets/window_icon.png', ])
        ])

        setup_kwargs['data_files'].extend([
            (os.path.join('share', mo_dir[6:]),
             [os.path.join(mo_dir, 'bajoo.mo')])
            for mo_dir in glob('bajoo/locale/*/LC_MESSAGES')])

        setup_kwargs['data_files'].extend([
            (os.path.join('share/icons/hicolor', mo_dir[19:], 'apps'),
             glob(os.path.join(mo_dir, "*")))
            for mo_dir in glob('bajoo/assets/icons/*')])

        setup_kwargs['include_package_data'] = False

# ############################################################################
# ### WINDOWS ################################################################
# ############################################################################

elif sys.platform in ['win32', 'win64']:
    setup_kwargs['install_requires'] += [
        'pypiwin32'
    ]
    setup_kwargs['setup_requires'] += [
        'py2exe'
    ]
    setup_kwargs['options'] = {
        'bdist_esky': {
            'freezer_module': 'py2exe',
            'freezer_options': {
                'dll_excludes': {
                    # Note that users will have to install
                    # VCRedist 2008 by themselves.
                    'msvcp90.dll',
                    'mpr.dll'  # system lib
                    'crypt32.dll'  # system lib required by gnupg
                },
                'skip_archive': True
            }
        }
    }

# ############################################################################
# ### MACOS ##################################################################
# ############################################################################

elif sys.platform == 'darwin':
    PYTHON_DIR = '/System/Library/Frameworks/Python.framework/Versions'
    PYTHON_LIB = PYTHON_DIR+'/2.7/lib/python2.7/'
    COPYRIGHT = (u"Copyright © 2016 Bajoo <support@bajoo.fr>, All Rights "
                 u"Reserved")

    py2app_options = {
        'plist': {
            'argv_emulation': True,
            'site_packages': True,
            'CFBundleIconFile': 'assets/exe_icon.icns',
            # keep the following in lower case because it is used to build
            # some path and esky only use lower case path
            'CFBundleName': 'bajoo',
            'CFBundleDisplayName': 'Bajoo',
            'CFBundleGetInfoString': "File sharing",
            'CFBundleIdentifier': "com.bajoo.osx.client",
            'CFBundleVersion': __version__,  # noqa
            'CFBundleShortVersionString': __version__,  # noqa
            'NSHumanReadableCopyright': COPYRIGHT,
            # disable the icon in the doc
            'LSUIElement': '1',
            'PyResourcePackages': [
                PYTHON_LIB,
                PYTHON_LIB+'lib-dynload/',
                PYTHON_LIB+'plat-mac/'
            ],
            'LSEnvironment': {
                'REQUESTS_CA_BUNDLE': '../Resources/cacert.pem'
            }
        },
        'frameworks': [
            # these libs are needed by gpg2
            '/usr/local/MacGPG2/lib/libz.1.2.8.dylib',
            '/usr/local/MacGPG2/lib/libintl.8.dylib',
            '/usr/local/MacGPG2/lib/libgcrypt.20.dylib',
            '/usr/local/MacGPG2/lib/libgpg-error.0.dylib',
            '/usr/local/MacGPG2/lib/libiconv.2.dylib',
            '/usr/local/MacGPG2/lib/libassuan.0.dylib',
        ],
        'resources': [
            '/usr/local/MacGPG2/bin/gpg2'
        ]
    }

    setup_kwargs['options'] = {
        'py2app': py2app_options,
        'bdist_esky': {
            'freezer_module': 'py2app',
            # need to duplicate py2app option here, esky does not seem able
            # to retrieve them from 'py2app' dict in 'options'
            'freezer_options': py2app_options
        }
    }

    setup_kwargs['app'] = ['start.py']
    setup_kwargs['setup_requires'].append('py2app')

    setup_kwargs['data_files'].extend([
        ('assets', ['bajoo/assets/bajoo.desktop',
                    'bajoo/assets/exe_icon.ico',
                    'bajoo/assets/exe_icon.icns',
                    'bajoo/assets/window_icon.png']),
        ('assets/images', glob('bajoo/assets/images/*.png')),
        ('assets/images/container_status',
         glob('bajoo/assets/images/container_status/*.png')),
        ('assets/images/trayicon_status',
         glob('bajoo/assets/images/trayicon_status/*.png'))
    ])

    setup_kwargs['data_files'].extend([
        (mo_dir[6:], [os.path.join(mo_dir, 'bajoo.mo')])
        for mo_dir in glob('bajoo/locale/*/LC_MESSAGES')])

    setup_kwargs['data_files'].extend([
        (os.path.join('icons', mo_dir[19:], 'apps'),
         glob(os.path.join(mo_dir, "*")))
        for mo_dir in glob('bajoo/assets/icons/*')])

    setup_kwargs['include_package_data'] = False

# ############################################################################
# ### DATA ###################################################################
# ############################################################################

if setup_kwargs['include_package_data']:
    setup_kwargs['package_data'] = {
        # Note: esky build doesn't support 'include_package_data'
        'bajoo': ['locale/*/LC_MESSAGES/*.mo', 'assets/*.png',
                  'assets/images/*.png', 'assets/images/*/*.png']
    }

# ############################################################################
# ### PYTHON 3 ###############################################################
# ############################################################################

if sys.version_info[0] is 3:  # Python3 only
    setup_kwargs['install_requires'] += [
        'wxpython-phoenix>=3.dev'
    ]
    setup_kwargs.setdefault('dependency_links', [])
    setup_kwargs['dependency_links'].append(
        'http://wxpython.org/Phoenix/snapshot-builds/')

# ############################################################################
# ### ESKY ###################################################################
# ############################################################################

try:
    from esky import bdist_esky
except ImportError:
    print("Warning: esky package not found. It is needed to build the "
          "distributable archives.")
else:
    if sys.platform in ['win32', 'cygwin', 'win64']:
        import requests

        if sys.version_info[0] is 2:  # Python 2
            try:
                import py2exe  # noqa
            except ImportError:
                print('Warning: To use esky, py2exe must be installed manually'
                      ' using this command:')
                print('\tpip install http://sourceforge.net/projects/py2exe/'
                      'files/latest/download?source=files')

        cacert_path = requests.certs.where()
        setup_kwargs['data_files'].extend((
            ('.', glob('gpg/*.exe') + glob('gpg/*.dll'),),
            ('requests', (cacert_path,),),))
        icon_path = './bajoo/assets/exe_icon.ico'

    elif sys.platform == 'darwin':
        import requests

        try:
            import py2app  # noqa
        except ImportError:
            print('Warning: To use esky, py2app must be installed manually'
                  ' using this command:')
            print('\tpip install --upgrade py2app')

        setup_kwargs['options']['py2app']['resources'].append(
            requests.certs.where()
        )
        icon_path = './assets/exe_icon.icns'

    if sys.platform in ['win32', 'cygwin', 'win64', 'darwin']:
        for f in glob('docs/*'):
            setup_kwargs['data_files'].extend((
                ('../%s' % f, glob('%s/*' % f),),))

        setup_kwargs['scripts'] = [
            bdist_esky.Executable('start.py', name='Bajoo', gui_only=True,
                                  icon=icon_path)
        ]


setup(**setup_kwargs)
