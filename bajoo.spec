# -*- mode: python -*-
# -*- coding: utf-8 -*-

import os
import pkg_resources
import sys

from PyInstaller.hooks.hookutils import collect_data_files


# Note: this script take the first entry point of the first distribution
# package found as the executable script.

# List distributions in the current directory.
distrib_list = list(pkg_resources.Environment('.'))

if not list(distrib_list):
    print('No distribution package found.')
    exit(1)

print('Using distribution package %s' % distrib_list[0])
print(pkg_resources.get_entry_info('bajoo', 'console_scripts', 'bajoo'))
script_list = pkg_resources.get_entry_map(distrib_list[0],
                                          'console_scripts')

if not script_list:
    print('No entry point found.')
    exit(1)

name, entry_point = script_list.items()[0]
print('Found entry point "%s"' % name)

pathex = [entry_point.dist.location]

script_path = os.path.join(WORKPATH, name + '-script.py')
print("Creating script for entry point %s" % name)

with open(script_path, 'w') as f:
    f.write("import %s\n" % entry_point.module_name)
    f.write("%s.%s()\n" % (entry_point.module_name,
                           '.'.join(entry_point.attrs)))


package_data = [(os.path.relpath(file, 'bajoo'), file, 'DATA')
                for [file, __] in collect_data_files('bajoo')]


a = Analysis([script_path],
             pathex=pathex,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

a.datas += package_data

pyz = PYZ(a.pure)

exe_name = name if sys.platform != 'win32' else '%s.exe' % name
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=exe_name,
          debug=False,
          strip=None,
          upx=True,
          console=False)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name=name)
