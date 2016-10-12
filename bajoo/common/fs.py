# -*- coding: utf-8 -*-

import ctypes
import os
import sys
from .strings import ensure_unicode


def hide_file_if_windows(file_path):
    """If running on Windows, set the file as hidden.

    On other platforms, do nothings.

    Args:
        file_path (unicode): target file path
    Raises:
        OSError
    """
    file_path = ensure_unicode(file_path)
    if sys.platform in ['win32', 'cygwin']:
        HIDDEN_FILE_ATTRIBUTE = 0x02
        ret = ctypes.windll.kernel32.SetFileAttributesW(
            file_path,
            HIDDEN_FILE_ATTRIBUTE)
        if not ret:
            raise ctypes.WinError()


try:
    replace_file = os.replace
except AttributeError:
    if sys.platform in ['win32', 'cygwin']:
        def replace_file(src, dst):
            """Move a file and replace the destination file (if any)

            This operation is atomic either on Windows and on POSIX platforms.

            Notes:
​                At least on Windows 10, using replace_file() don't preserve
                the HIDDEN file attribute.

            Args:
                src (unicode): source path
                dst (unicode): destination path
            Raises:
                OSError, IOError
            """
            src = ensure_unicode(src)
            dst = ensure_unicode(dst)
            MOVEFILE_REPLACE_EXISTING = 1
            ret = ctypes.windll.kernel32.MoveFileExW(
                src, dst, MOVEFILE_REPLACE_EXISTING)
            if not ret:
                raise ctypes.WinError()
    else:
        replace_file = os.rename
