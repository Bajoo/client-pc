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
from .service import Service


# Start network worker at start.
_service = Service()

_service.start()
atexit.register(_service.stop)

# Copy methods from the service instance.
json_request = _service.json_request
download = _service.download
upload = _service.upload


if __name__ == "__main__":
    import os
    import io
    import logging
    from .proxy import prepare_proxy

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
