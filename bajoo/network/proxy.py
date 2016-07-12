# -*- coding: utf-8 -*-

import logging
import re
import requests
import socket
import socks
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from ..common.i18n import N_
from .errors import ProxyError

_logger = logging.getLogger(__name__)

_default_socket = socket.socket

# If set, tuple of the form (type, uri, port, username, password).
# Eg: ('socks4', '192.168.1.1', 9000, 'admin', 'admin')
_actual_socks_config = None

PROXY_MODE_SYSTEM = 'system_settings'
PROXY_MODE_MANUAL = 'manual_settings'
PROXY_MODE_NO = 'no_proxy'


def _request_socks_proxy_support():
    """Check if Request has support for socks proxy.

    Returns:
        bool: True if it has; False otherwise.
    """
    # Requests have socks support since version 3.10.0 only
    req_version = tuple((int(x) if x.isdigit() else 9999)
                        for x in requests.__version__.split('.'))
    return req_version > (3, 10, 0)


def prepare_proxy(proxy_mode, settings=None):
    """Apply the proxy configuration before a requests.

    Args:
        proxy_mode (str): Indicate from where the proxy settings are obtained.
            Must be one of 'system_settings', 'manual_settings', or 'no_proxy'.
        settings (dict): in 'manual_settings' mode, effective proxy settings.
            It uses the following config settings  (all are required):
            - type
            - url
            - port
            - user
            - password

    Returns:
        dict: proxy config to pass to the requests library.
    """

    # mode no proxy: ignores system settings.
    if proxy_mode == PROXY_MODE_NO:
        _logger.info('Use no proxy')
        _disable_socks_proxy()
        return {}

    # mode manual proxy
    if proxy_mode == PROXY_MODE_MANUAL:
        settings = settings or {}

        # proxy_type should be 'HTTP', 'SOCKS4' or 'SOCKS5'.
        proxy_type = settings.get('type').lower()
        proxy_url = settings.get('url')
        proxy_port = settings.get('port')
        proxy_user = settings.get('user')
        proxy_password = settings.get('password')

        if (proxy_type in ('socks4', 'socks5') and
                not _request_socks_proxy_support()):
            _enable_socks_proxy(proxy_type, proxy_url, proxy_port,
                                proxy_user, proxy_password)
            return {}

        if not proxy_url:
            raise ProxyError(None,
                             N_('Proxy is activate, but no URL is present.\n'
                                'Check your configuration.'))

        _disable_socks_proxy()

        # parse the host name the proxy url
        proxy_string = urlparse(proxy_url).hostname or proxy_url

        # add the port number
        if proxy_port:
            proxy_string = '%s:%s' % (proxy_string, proxy_port)

        # add user & password
        if proxy_user:
            user = proxy_user

            if proxy_password:
                user += ':' + proxy_password + '@'  # user:pass@

            proxy_string = user + proxy_string  # user:pass@any.proxy.addr:port

        # type://user:pass@any.proxy.addr:port
        proxy_string = proxy_type + "://" + proxy_string

        return {'https': proxy_string}

    if proxy_mode != PROXY_MODE_SYSTEM:
        _logger.warning('Unknown proxy mode "%s"; Use system settings.'
                        % proxy_mode)

    # mode system settings (default)
    _disable_socks_proxy()
    return None


def _enable_socks_proxy(proxy_type, host, port, username, password):
    """Patch the socket to use SOCKS proxy.
    Args:
        proxy_type (str): either 'socks4' or 'socks5'
        host (str)
        port (int)
        username (str)
        password (str)
    """
    global _actual_socks_config

    if _actual_socks_config == (proxy_type, host, port, username, password):
        return

    _logger.info('Patch socket to use SOCKS proxy')
    _actual_socks_config = (proxy_type, host, port, username, password)

    # remove optional scheme
    host = re.match(r'(socks[45]?://)?(.*)', host).groups()[1]
    proxy_type = socks.SOCKS4 if proxy_type == 'socks4' else socks.SOCKS5
    socks.set_default_proxy(proxy_type, host, port, username=username,
                            password=password)
    socket.socket = socks.socksocket


def _disable_socks_proxy():
    """restore the initial socket if a socks proxy is enabled."""
    global _actual_socks_config

    if _actual_socks_config is not None:
        _logger.info('Reset default socket (without SOCKS proxy)')
        socket.socket = _default_socket
        _actual_socks_config = None
