# -*- coding: utf-8 -*-

import io
import logging
import tempfile

from requests import Session
from requests.adapters import HTTPAdapter

from . import errors
from .proxy import prepare_proxy

_logger = logging.getLogger(__name__)

# Maximum number of automatic retry in case of connexion error
# HTTP errors (4XX and 5XX) are not retried.
MAX_RETRY = 3


def _prepare_session():
    """Prepare a session to send an HTTPS request, with auto retry.

    Returns:
        requests.Session: new HTTP session
    """
    session = Session()
    adapter = HTTPAdapter(max_retries=MAX_RETRY)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


@errors.handler
def json_request(request):
    """Performs a json HTTP requests, then returns the result.

    Args:
        request (Request):
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': JSON response.
    """
    params = request.params
    session = _prepare_session()
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
    response = session.request(method=request.verb, url=request.url, **params)

    _logger.log(5, 'request %s -> %s', request, response.status_code)

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
def download(request):
    """Performs a download HTTP requests, then returns the result.

    Args:
        request (Request):
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': a temporary File-like object containing the downloaded
            file.
    """
    params = request.params
    session = _prepare_session()
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
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
def upload(request):
    """Performs an upload HTTP requests, then returns the result.

    Args:
        request (Request):
    Returns:
        dict: contains 3 keys:
          - 'code': the HTTP response code
          - 'headers': a dict containing all headers (key: value)
          - 'content': set to None.
    """
    params = request.params
    session = _prepare_session()
    params.setdefault('timeout', 4)
    params.setdefault('proxies', prepare_proxy())
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