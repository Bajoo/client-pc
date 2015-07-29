# -*- coding: utf-8 -*-

import io
import logging
import os
import tempfile

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from concurrent.futures import ThreadPoolExecutor, CancelledError
from requests import Session
from requests.adapters import HTTPAdapter

from ..common import config
from ..common.future import patch
from .request_future import RequestFuture
from . import errors


_logger = logging.getLogger(__name__)

control_thread_pool = ThreadPoolExecutor(max_workers=2)
data_thread_pool = ThreadPoolExecutor(max_workers=2)
# TODO: configurable max_workers

PROXY_MODE_SYSTEM = 'system_settings'
PROXY_MODE_MANUAL = 'manual_settings'
PROXY_MODE_NO = 'no_proxy'


def _prepare_proxy():
    proxy_mode = config.get('proxy_mode')

    # mode no proxy
    if proxy_mode == PROXY_MODE_NO:
        return {}

    # mode manual proxy
    if proxy_mode == PROXY_MODE_MANUAL:
        proxy_type = config.get('proxy_type').lower()
        proxy_url, proxy_port = \
            config.get('proxy_url'), config.get('proxy_port')
        proxy_user, proxy_password = \
            config.get('proxy_user'), \
            config.get('proxy_password')

        if not proxy_url:
            # TODO: config-specific exception
            raise Exception

        # parse the host name the proxy url

        proxy_string = urlparse(proxy_url).hostname  # any.proxy.addr

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

    # mode system settings (default)
    return None


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


def _get_thread_pool(**params):
    """
    Get the appropriate thread pool corresponding to a priority level.

    Args:
        has_priority: (boolean) the expected priority level.
            If set to True, is has priority; False otherwise.

    Returns:
        the thread pool corresponding to the priority level
    """
    global control_thread_pool, data_thread_pool
    priority = params.get('has_priority', False)

    return control_thread_pool if priority \
        else data_thread_pool


def json_request(verb, url, **params):
    """
    Send a request and get the json from its response.

    Args:
        verb: (str)
        url: (str)
        params: additional parameters
            - has_priority: (boolean) set request priority (by default True)

    Returns: Future<dict>
        A Future object containing the json object from the response
    """
    shared_data = {
        'cancelled': False
    }
    params = dict(params)

    @errors.handler
    def _json_request():
        session = _prepare_session(url)
        params.setdefault('timeout', 4)
        params.setdefault('proxies', _prepare_proxy())
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

    thread_pool = _get_thread_pool(**params)
    future = patch(thread_pool.submit(_json_request))

    return RequestFuture(future, shared_data)


def download(verb, url, **params):
    """
    Download a file and save it as a temporary file.

    Args:
        verb: (str)
        url: (str)
        params: additional parameters
            - has_priority: (boolean) set request priority (by default True)

    Returns: Future<File>
        A Future object contains the temporary file object
    """
    shared_data = {
        'cancelled': False
    }
    params = dict(params)

    @errors.handler
    def _download():
        session = _prepare_session(url)
        params.setdefault('timeout', 4)
        params.setdefault('proxies', _prepare_proxy())
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
            # the result will be ignore if the flag 'cancelled' is turned on
            if chunk and not shared_data['cancelled']:
                temp_file.write(chunk)
                downloaded_bytes += len(chunk)

        if shared_data['cancelled']:
            _logger.debug("Download of %s cancelled (%d bytes received)",
                          url, downloaded_bytes)
        else:
            _logger.debug("Downloaded %s bytes from %s",
                          downloaded_bytes, url)

        session.close()

        if shared_data['cancelled']:
            temp_file.close()
            return None

        # Move the pointer of the file stream to zero
        # and not close it, for it can be read outside.
        temp_file.seek(0)

        return {
            'code': response.status_code,
            'headers': response.headers,
            'content': temp_file
        }

    thread_pool = _get_thread_pool(**params)
    future = patch(thread_pool.submit(_download))

    return RequestFuture(future, shared_data)


def upload(verb, url, source, **params):
    """
    Upload a file to an address.

    Note: if a file-like object is passed as source, it will be automatically
    closed after the upload.

    Args:
        verb: (str)
        url: (str)
        source (str/File): Path of the file to upload (if type is str), or
            file-like object to upload.
        params: additional parameters
            - has_priority: (boolean) set request priority (by default True)
    """
    shared_data = {
        'cancelled': False
    }
    params = dict(params)

    @errors.handler
    def _upload():
        session = _prepare_session(url)
        params.setdefault('timeout', 4)
        params.setdefault('proxies', _prepare_proxy())
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

    thread_pool = _get_thread_pool(**params)
    future = patch(thread_pool.submit(_upload))

    return RequestFuture(future, shared_data)


if __name__ == "__main__":
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)
    _logger.debug('get proxy: %s', _prepare_proxy())

    # Test JSON_request
    json_future = json_request('GET', 'http://ip.jsontest.com/')
    _logger.debug("JSON response content: %s", json_future.result())

    # Test download
    # Remove file before downloading
    sample_file_name = "sample.pdf"
    if os.path.exists(sample_file_name):
        os.remove(sample_file_name)

    future_download = download('GET', 'http://www.pdf995.com/samples/pdf.pdf')
    with io.open(sample_file_name, "wb") as sample_file, \
            future_download.result()['content'] as tmp_file:
        sample_file.write(tmp_file.read())

    # Test cancel a request, this should throw a CancelledError
    import time

    print('Start a download ...')
    future_download = download('GET', 'http://www.pdf995.com/samples/pdf.pdf')
    time.sleep(0.5)
    print('... then cancel it!')
    future_download.cancel()
    try:
        result = future_download.result()
        print('Cancel failed ? result: HTTP %s' % result.get('code'))
    except CancelledError:
        print('CanceledError raised, as expected.')
