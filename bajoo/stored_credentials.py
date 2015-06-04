# -*- coding: utf-8 -*-
"""Functions to load and store user credentials persistently."""

import logging

_logger = logging.getLogger(__name__)


def load():
    """Load and returns the last saved credentials, from the disk.
    Returns:
        (str, str): username and refresh token loaded. If only the username is
            present, the second returned part is None. If nothing is found,
            (None, None) is returned.
    """
    username, refresh_token = None, None
    # TODO: to implement

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
    # TODO: to implement
