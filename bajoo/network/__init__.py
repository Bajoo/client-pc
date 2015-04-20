# -*- coding: utf-8 -*-
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from requests import Session
from requests.adapters import HTTPAdapter


_logger = logging.getLogger(__name__)

control_thread_pool = ThreadPoolExecutor(max_workers=2)
data_thread_pool = ThreadPoolExecutor(max_workers=2)
# TODO: configurable max_workers


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


def json_request(verb, url, **params):
    """
    Send a request and get the json from its response.

    Args:
        verb: (str)
        url: (str)
        params: additional parameters

    Returns: Future<dict>
        A Future object containing the json object from the response
    """

    def _json_request():
        session = _prepare_session(url)
        response = session.request(method=verb, url=url, **params)

        _logger.debug('JSON Request %s %s -> %s',
                      verb, url, response.status_code)

        response.raise_for_status()

        session.close()
        return response.json()

    global control_thread_pool
    return control_thread_pool.submit(_json_request)


def download(verb, url, **params):
    """
    Download a file and save it as a temporary file.

    Args:
        verb: (str)
        url: (str)
        params: additional parameters

    Returns: Future<File>
        A Future object contains the temporary file object
    """

    def _download():
        session = _prepare_session(url)
        response = session.request(method=verb, url=url, stream=True, **params)

        _logger.debug("%s downloading from %s -> %s",
                      verb, url, response.status_code)

        response.raise_for_status()

        # Read response content and write to temporary file
        temp_file = tempfile.SpooledTemporaryFile(
            max_size=524288, suffix=".tmp")

        for chunk in response.iter_content(1024):
            if chunk:
                temp_file.write(chunk)

        session.close()

        # Move the pointer of the file stream to zero
        # and not close it, for it can be read outside.
        temp_file.seek(0)
        return temp_file

    global data_thread_pool
    return data_thread_pool.submit(_download)


def upload(verb, url, source, **params):
    """
    Upload a file to an address.

    Args:
        verb: (str)
        url: (str)
        source: (str/File)
        params: additional parameters
    """

    def _upload():
        session = _prepare_session(url)
        file = source

        if isinstance(file, str):
            # If 'file' is a filename, open it
            file = open(file, 'rb')

        with file:
            # TODO: search a way to cancel this upload
            response = session.request(method=verb, url=url,
                                       files={'file': file}, **params)

            _logger.debug("%s uploading from %s -> %s",
                          verb, url, response.status_code)

            response.raise_for_status()

    global data_thread_pool
    return data_thread_pool.submit(_upload)


if __name__ == "__main__":
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    # Test JSON_request
    json_future = json_request('GET', 'http://ip.jsontest.com/')
    _logger.debug("JSON response content: %s", json_future.result())

    # Test download
    # Remove file before downloading
    sample_file_name = "sample.pdf"
    if os.path.exists(sample_file_name):
        os.remove(sample_file_name)

    future_download = download('GET', 'http://www.pdf995.com/samples/pdf.pdf')
    with open(sample_file_name, "wb") as sample_file, \
            future_download.result() as tmp_file:
        sample_file.write(tmp_file.read())

    _logger.debug("Downloaded file's size: %d bytes",
                  os.stat(sample_file_name).st_size)
    # TODO: Test upload
