# -*- coding: utf-8 -*-

import io
import logging
import tempfile

from requests import Session
from requests.adapters import HTTPAdapter

from . import errors
from .proxy import prepare_proxy

_logger = logging.getLogger(__name__)


def _prepare_session(url):
    """
    Prepare a session to send an HTTP request, with a possibility of retrying.

    Args:
        url: (string)

    Returns:
        a Session() object to send request.
    """
    session = Session()

    # TODO: make 'max_retries' configurable
    session.mount(url, HTTPAdapter(max_retries=1))

    return session


@errors.handler
def json_request(verb, url, **params):
    session = _prepare_session(url)
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
    response = session.request(method=verb, url=url, **params)

    _logger.debug('JSON Request %s %s -> %s',
                  verb, url, response.status_code)

    response.raise_for_status()
    session.close()

    content = None
    if response.content:
        content = response.json()

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': content
    }


@errors.handler
def download(verb, url, **params):
    session = _prepare_session(url)
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
    response = session.request(method=verb, url=url, stream=True, **params)

    _logger.debug("%s downloading from %s -> %s",
                  verb, url, response.status_code)

    response.raise_for_status()

    # Read response content and write to temporary file
    temp_file = tempfile.SpooledTemporaryFile(
        max_size=524288, suffix=".tmp")

    downloaded_bytes = 0
    chunk_size = 1024

    for chunk in response.iter_content(chunk_size):
        if chunk:
            temp_file.write(chunk)
            downloaded_bytes += len(chunk)

    _logger.debug("Downloaded %s bytes from %s", downloaded_bytes, url)

    session.close()

    # Move the pointer of the file stream to zero
    # and not close it, for it can be read outside.
    temp_file.seek(0)

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': temp_file
    }


@errors.handler
def upload(verb, url, source, **params):
    session = _prepare_session(url)
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
    file = source

    try:
        if isinstance(file, basestring):
            # If 'file' is a filename, open it
            file = io.open(file, 'rb')
    except NameError:
        if isinstance(file, str):
            # If 'file' is a filename, open it
            file = io.open(file, 'rb')

    with file:
        _logger.debug("Start %s uploading to %s", verb, url)

        # TODO: search a way to cancel this upload
        response = session.request(method=verb, url=url,
                                   data=file, **params)

        _logger.debug("%s upload to %s -> %s",
                      verb, url, response.status_code)

        response.raise_for_status()

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': None
    }
