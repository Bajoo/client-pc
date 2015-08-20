# -*- coding: utf-8 -*-

import os.path
import sys


def is_path_allowed(file_path):
    """Check if a file path is allowed to be synced.

    Some files must not be sync, for different reasons: the path can contains
    some name forbidden by the operating system, or of special meanings.

    Also, Bajoo index files must be ignored by the sync.
    """

    (dir_part, filename) = os.path.split(file_path)
    if filename.startswith('.bajoo'):
        return False  # Bajoo container index

    if filename == '.key':
        return False  # Container encryption key

    if sys.platform in ['win32', 'cygwin', 'win64']:
        reserved_characters = '<>:"/\|?*' + ''.join(chr(i) for i in range(31))
        reserved_filename = ['CON', 'PRN', 'AUX', 'NUL']
        reserved_filename += list('COM%d' % i for i in range(1, 9))
        reserved_filename += list('LPT%d' % i for i in range(1, 9))

        if any(c in reserved_characters for c in filename):
            return False

        if filename.split('.')[0] in reserved_filename:
            return False

    return True
