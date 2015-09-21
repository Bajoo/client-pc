# -*- coding: utf-8 -*-

import ctypes
import logging
import os.path
import sys
if sys.platform == "darwin":
    import Foundation

_logger = logging.getLogger(__name__)


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


def is_hidden(path):
    """Portable way to check whether a file is hidden.

    Args:
        path (str): file path to check.
    Returns:
        boolean: True or False whether the file is file
    """
    abs_path = os.path.abspath(path)
    name = os.path.basename(abs_path)

    if sys.platform == 'win32':
        return _is_hidden_under_windows(abs_path)
    else:
        if name.startswith('.'):
            return True
        if sys.platform == 'darwin':
            return _is_hidden_under_darwin(abs_path)
    return False


def _is_hidden_under_windows(path):
    try:
        res = ctypes.windll.kernel32.GetFileAttributesW(path)
        if not res or res == -1:
            raise ctypes.WinError()
        return bool(res & 0x02)
    except:
        _logger.warning('Check file attributes of %s failed' % path,
                        exc_info=True)
        return False


def _is_hidden_under_darwin(path):
    # see http://stackoverflow.com/a/15236292/1109005
    url = Foundation.NSURL.fileURLWithPath_(path)
    res = url.getResourceValue_forKey_error_(
        None, Foundation.NSURLIsHiddenKey, None)
    return res[1]
