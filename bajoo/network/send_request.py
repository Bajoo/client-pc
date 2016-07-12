# -*- coding: utf-8 -*-

import io
import logging

from ..data import ChunkData
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

    with response.raw:
        data = ChunkData(response.raw,
                         hint_size=response.headers.get('content-length'),
                         hint_md5=response.headers.get('etag'))

    _logger.log(5, "Downloaded %s bytes from %s",
                data.total_size, request.url)

    return {
        'code': response.status_code,
        'headers': response.headers,
        'content': data.file
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
