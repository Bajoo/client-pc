# -*- coding: utf-8 -*-
"""Helpers function to find Bajoo path folders."""

import errno
import logging
import os
import pkg_resources
import sys
import appdirs

_logger = logging.getLogger(__name__)


_appdirs = appdirs.AppDirs(appname='Bajoo2', appauthor=False, roaming=True)


def _ensure_dir_exists(dir_path):
    """Try to create the folder if it not exists.

    If an error occurs, a warning log is sent and the error is ignored.
    """
    try:
        os.makedirs(dir_path)
        _logger.debug('Created missing folder "%s"' % dir_path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(dir_path):
            pass
        else:
            _logger.warning('Unable to create the missing folder "%s"'
                            % dir_path, exc_info=True)


def get_log_dir():
    """Returns the directory path containing Bajoo log files."""
    log_dir = _appdirs.user_log_dir
    _ensure_dir_exists(log_dir)
    return log_dir


def get_cache_dir():
    """Returns the directory path containing Bajoo cache data."""
    cache_dir = _appdirs.user_cache_dir
    _ensure_dir_exists(cache_dir)
    return cache_dir


def get_config_dir():
    """Returns the directory path containing Bajoo config files."""
    config_dir = _appdirs.user_config_dir
    _ensure_dir_exists(config_dir)
    return config_dir


def get_data_dir():
    """Returns the directory path containing Bajoo data files."""
    data_dir = _appdirs.user_data_dir
    _ensure_dir_exists(data_dir)
    return data_dir


def resource_filename(resource):
    """Returns the correct filename of the package_data resource."""

    # Note: it works only in non-zipped mode.
    if getattr(sys, 'frozen', False) and getattr(sys, 'executable', False):
        dir_executable = os.path.dirname(sys.executable)
        result_path = os.path.join(dir_executable, 'bajoo', resource)
    else:
        result_path = pkg_resources.resource_filename('bajoo', resource)
    if sys.version_info[0] is 2 and isinstance(result_path, str):
        # pkg_resources.resource_filename don't always returns unicode values.
        # With Python 2.7 on Windows 10 (french settings), we have a
        # latin1-encoded result of type 'str'.
        return result_path.decode(sys.getfilesystemencoding())
    return result_path

def default_root_folder():
    """Returns the default emplacement fir the Bajoo root folder."""
    return os.path.join(os.path.expanduser('~'), 'Bajoo')


def main():
    print('log dir: %s' % get_log_dir())
    print('cache dir: %s' % get_cache_dir())
    print('config dir: %s' % get_config_dir())
    print('data dir: %s' % get_data_dir())
    print('')
    print('default Bajoo root folder: %s', default_root_folder())

if __name__ == "__main__":
    main()
