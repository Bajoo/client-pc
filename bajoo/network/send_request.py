# -*- coding: utf-8 -*-

import io
import logging
import tempfile

from . import errors

_logger = logging.getLogger(__name__)


@errors.handler
def json_request(request, session, proxy_settings=None):
    """Performs a json HTTP requests, then returns the result.

    Args:
        request (Request):
        session (requests.Session)
        proxy_settings (dict, optional): proxy settings to pass to the requests
            library.
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': JSON response.
    """
    params = request.params
    params.setdefault('proxies', proxy_settings)
    response = session.request(method=request.verb, url=request.url, **params)

    _logger.log(5, 'request %s -> %s', request, response.status_code)

    response.raise_for_status()

    content = None
    if response.content:
        content = response.json()

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': content
    }


@errors.handler
def download(request, session, proxy_settings=None):
    """Performs a download HTTP requests, then returns the result.

    Args:
        request (Request):
        session (requests.Session)
        proxy_settings (dict, optional): proxy settings to pass to the requests
            library.
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': a temporary File-like object containing the downloaded
            file.
    """
    params = request.params
    params.setdefault('proxies', proxy_settings)
    response = session.request(method=request.verb, url=request.url,
                               stream=True, **params)

    _logger.log(5, "request %s -> %s", request, response.status_code)

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

    _logger.log(5, "Downloaded %s bytes from %s",
                downloaded_bytes, request.url)

    # Move the pointer of the file stream to zero
    # and not close it, for it can be read outside.
    temp_file.seek(0)

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': temp_file
    }


@errors.handler
def upload(request, session, proxy_settings=None):
    """Performs an upload HTTP requests, then returns the result.

    Args:
        request (Request):
        session (requests.Session)
        proxy_settings (dict, optional): proxy settings to pass to the requests
            library.
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': set to None.
    """
    params = request.params
    params.setdefault('proxies', proxy_settings)
    file = request.source

    try:
        if isinstance(file, basestring):
            # If 'file' is a filename, open it
            file = io.open(file, 'rb')
    except NameError:
        if isinstance(file, str):
            # If 'file' is a filename, open it
            file = io.open(file, 'rb')

    with file:
        _logger.log(5, "start request %s", request)

        response = session.request(method=request.verb, url=request.url,
                                   data=file, **params)

        _logger.log(5, "request %s -> %s", request, response.status_code)

        response.raise_for_status()

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': None
    }
