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


Examples:

    Use of json_request:

    >>> with Service() as service:
    ...     promise = service.json_request(
    ...         'GET', 'https://api.bajoo.fr/healthcheck')
    ...     # Raises an exception if the request takes more than 10 seconds.
    ...     result_dict = promise.result(10)
    ...     print(result_dict['content'])
    {u'status': u'ok'}

    Use of download:

    >>> import tempfile
    >>> with Service() as service:
    ...     promise = service.download(
    ...         'GET', 'https://www.bajoo.fr/favicon.ico')
    ...     result = promise.result(10)
    ...     with tempfile.TemporaryFile('wb') as target_file:
    ...         buffer = result['content'].read(10240)
    ...         while buffer:
    ...             target_file.write(buffer)
    ...             buffer = result['content'].read(10240)
"""

from . import errors  # noqa
from .service import Service


class Context(object):
    def __init__(self):
        self._service = None

    def start(self):
        global json_request, download, upload, set_proxy

        self._service = Service()
        self._service.start()

        # Copy methods from the service instance.
        json_request = self._service.json_request
        download = self._service.download
        upload = self._service.upload
        set_proxy = self._service.set_proxy

    def stop(self):
        global json_request, download, upload, set_proxy

        if self._service:
            self._service.stop()

        json_request = None
        download = None
        upload = None
        set_proxy = None

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# The context must be used to set theses methods.
json_request = None
download = None
upload = None
set_proxy = None
