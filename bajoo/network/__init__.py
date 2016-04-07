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
from .request import Request


# Start network worker at start.
executor.start()
atexit.register(executor.stop)


def json_request(verb, url, priority=10, **params):
    """
    Send a request and get the json from its response.

    Args:
        verb: (str)
        url: (str)
        priority (int, optional): requests with lower priority are executed
            first. Default to 10 (high priority)
        params: additional parameters
    Returns: Future<dict>
        A Future object containing the json object from the response
    """
    params = dict(params)
    request = Request(Request.JSON, verb, url, params, priority=priority)
    return executor.add_task(request)


def download(verb, url, priority=100, **params):
    """
    Download a file and save it as a temporary file.

    Args:
        verb: (str)
        url: (str)
        priority (int, optional): requests with lower priority are executed
            first. Default to 100 (normal priority)
        params: additional parameters
    Returns: Future<File>
        A Future object contains the temporary file object
    """
    params = dict(params)
    request = Request(Request.DOWNLOAD, verb, url, params, priority=priority)
    return executor.add_task(request)


def upload(verb, url, source, priority=100, **params):
    """
    Upload a file to an address.

    Note: if a file-like object is passed as source, it will be automatically
    closed after the upload.

    Args:
        verb: (str)
        url: (str)
        source (str/File): Path of the file to upload (if type is str), or
            file-like object to upload.
        priority (int, optional): requests with lower priority are executed
            first. Default to 100 (normal priority)
        params: additional parameters
    """
    params = dict(params)
    request = Request(Request.UPLOAD, verb, url, params, source, priority)
    return executor.add_task(request)


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
