# -*- coding: utf-8 -*-
"""Functions to load and store user credentials persistently."""

import errno
import io
import json
import logging
import os.path

from .common.path import get_config_dir

_logger = logging.getLogger(__name__)


def load():
    """Load and returns the last saved credentials, from the disk.
    Returns:
        (str, str): username and refresh token loaded. If only the username is
            present, the second returned part is None. If nothing is found,
            (None, None) is returned.
    """
    username, refresh_token = None, None
    token_path = os.path.join(get_config_dir(), 'token')
    file_content = None

    try:
        with io.open(token_path, 'r', encoding='utf-8') as token_file:
            file_content = json.load(token_file)
    except (IOError, OSError) as error:
        if error.errno == errno.ENOENT:
            _logger.info('refresh_token file not found.')
        else:
            _logger.warning('Unable to load refresh_token file:',
                            exc_info=True)
        return None, None
    except ValueError:
        _logger.warning('Unable to load refresh_token file:', exc_info=True)
        return None, None

    try:
        username = file_content[0]
        refresh_token = file_content[1]
    except (IndexError, KeyError):
        _logger.warning('Error when loading refresh_token file:',
                        exc_info=True)
        return username, refresh_token

    _logger.debug('credentials loaded: username="%s" token %s' %
                  (username, 'found' if refresh_token else 'not found'))
    return username, refresh_token


def save(username, refresh_token=None):
    """Save the credentials on the disk.
    Args:
        username (str): username (email)
        refresh_token (str, optional): OAuth2 refresh token.
    """
    _logger.debug('Credentials saved on disk.')

    token_path = os.path.join(get_config_dir(), 'token')
    try:
        with open(token_path, 'w') as token_file:
            json.dump([username, refresh_token], token_file)
    except (IOError, OSError, ValueError):
        _logger.warning('Unable to save refresh_token file:', exc_info=True)
