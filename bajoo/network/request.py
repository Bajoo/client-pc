# -*- coding: utf-8 -*-

import io
import functools
import logging
import tempfile

from requests import Session
from requests.adapters import HTTPAdapter

from . import errors
from .proxy import prepare_proxy

_logger = logging.getLogger(__name__)


@functools.total_ordering
class Request(object):
    """Represents a request waiting to be executed.

    Attributes:
        action (str): one of 'UPLOAD', 'DOWNLOAD' or 'JSON'. Set how to handle
            upload and download.
        verb (str): HTTP verb
        url (str): HTTP URL
        params (dict):
        source (str / File-like): if action is 'UPLOAD', source file.
            It can be a File-like object (in which case it will be send as is),
            or a str containing the path of the file to send.
        priority (int): Request priority. requests of lower priority
            are executed first. Default to 100.
        increment_id (int): unique ID set when the request is added to the
            queue. It's used as in comparison to find which requests must be
            prioritized: at equal priority, first-created requests (ie, with a
            smaller increment_id) are executed first.
    """

    UPLOAD = 'UPLOAD'
    DOWNLOAD = 'DOWNLOAD'
    JSON = 'JSON'

    def __init__(self, action, verb, url, params, source=None, priority=100):
        self.action = action
        self.verb = verb
        self.url = url
        self.params = params
        self.source = source
        self.priority = priority
        self.increment_id = None

    def __str__(self):
        return '%s (%s) %s' % (self.verb, self.action, self.url)

    def __eq__(self, other):
        return (self.priority == other.priority and
                self.increment_id == other.increment_id)

    def __lt__(self, other):
        return ((self.priority, self.increment_id) <
                (other.priority, other.increment_id))


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
def json_request(request):
    verb, url, params = request.verb, request.url, request.params
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
def download(request):
    verb, url, params = request.verb, request.url, request.params
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
def upload(request):
    verb, url, source, params = request.verb, request.url, \
                                request.source, request.params
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
