# -*- coding: utf-8 -*-
"""Network module

This module performs HTTPS requests to the Bajoo API. All requests are
asynchronous, executed in separate threads.

Three main function are available, to upload a file, download a file, or send
a JSON request. Each of these functions returns a Promise instance.

This module uses the `config` module to configure the proxy settings, and
bandwidths limitation.

In case of error, an Exception is returned ready to be displayed to the user.
The message is human-readable and marked for translation (but not translated).

The module has a status, who can be disconnected, connected, or error. When an
error happens many times, the status changes according to this error.
- ConnectionError and HTTP 503 errors are 'disconnected'
- ProxyError, HTTP 500 errors are 'error'
When we are not connected, requests are done periodically, to check if the
status has changed. As soon as the Bajoo servers responds a 200 OK, the status
is updated.

"""

import atexit
from . import errors  # noqa
from . import executor
from .executor import start, stop  # noqa
from .proxy import prepare_proxy


# Start network worker at start.
executor.start()
atexit.register(executor.stop)


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
    params = dict(params)
    priority = 100
    if params.get('has_priority', False):
        priority = 10
    return executor.add_task('REQUEST', verb, url, params, priority=priority)


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
    params = dict(params)
    priority = 100
    if params.get('has_priority', False):
        priority = 10
    return executor.add_task('DOWNLOAD', verb, url, params, priority=priority)


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
    params = dict(params)
    params['source'] = source
    priority = 100
    if params.get('has_priority', False):
        priority = 10
    return executor.add_task('UPLOAD', verb, url, params, priority=priority)


if __name__ == "__main__":
    import os
    import io
    import logging

    logging.basicConfig(level=logging.DEBUG)
    print('get proxy: %s' % prepare_proxy())

    # Test JSON_request
    json_future = json_request('GET', 'http://ip.jsontest.com/')
    print("JSON response content: %s" % json_future.result())

    # Test download
    # Remove file before downloading
    sample_file_name = "sample.pdf"
    if os.path.exists(sample_file_name):
        os.remove(sample_file_name)

    future_download = download('GET', 'http://www.pdf995.com/samples/pdf.pdf')
    with io.open(sample_file_name, "wb") as sample_file, \
            future_download.result()['content'] as tmp_file:
        sample_file.write(tmp_file.read())
