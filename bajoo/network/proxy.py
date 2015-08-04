# -*- coding: utf-8 -*-

import logging
import re
import socket
import socks
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from ..common import config
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


def prepare_proxy():
    """Apply the proxy configuration before a requests.

    It uses the following config settings:
    - proxy_type (expected to be 'system_settings', 'manual_settings',
        or 'no_proxy'
    - proxy_url
    - proxy_port
    - proxy_user
    - proxy_password

    returns:
        dict: proxy config to pass to the requests library.
    """
    proxy_mode = config.get('proxy_mode')

    # mode no proxy: ignores system settings.
    if proxy_mode == PROXY_MODE_NO:
        _disable_socks_proxy()
        return {}

    # mode manual proxy
    if proxy_mode == PROXY_MODE_MANUAL:

        # proxy_type should be 'HTTP', 'SOCKS4' or 'SOCKS5'.
        proxy_type = config.get('proxy_type').lower()
        proxy_url = config.get('proxy_url')
        proxy_port = config.get('proxy_port')
        proxy_user = config.get('proxy_user')
        proxy_password = config.get('proxy_password')

        if proxy_type in ('socks4', 'socks5'):
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
        _logger.warning('Unknwon proxy mode "%s"; Use system settings.'
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
