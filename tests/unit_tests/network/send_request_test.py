# -*- coding: utf-8 -*-

import io
import random

import pytest
import requests

from bajoo.network import send_request
from bajoo.network.errors import ConnectionError, HTTPError, \
    InterruptedDownloadError, NetworkError
from bajoo.network.request import Request


class TestSendRequest(object):

    session = None

    def setup(self):
        self.session = requests.Session()

    def teardown(self):
        self.session.close()

    def test_json_request(self, http_server):

        url = '%s?response=%s' % (http_server.base_uri, '{"foo":"bar"}')
        req = Request(Request.JSON, 'GET', url, {})

        with http_server:
            result = send_request.json_request(req, self.session)

        assert result.get('code') is 200
        assert 'foo' in result.get('content')
        assert result.get('content').get('foo') == 'bar'

    def test_download(self, http_server):
        binary_file = bytearray(random.getrandbits(8) for _ in range(4096))

        def handler(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(binary_file)

        http_server.handler.do_GET = handler

        req = Request(Request.DOWNLOAD, 'GET', http_server.base_uri, {})
        with http_server:
            result = send_request.download(req, self.session)

        assert result.get('code') is 200

        buffer = b''
        with result.get('content') as dl_file:
            buffer += dl_file.read()
        assert buffer == binary_file

    def test_download_interrupted(self, http_server):
        binary_file = bytearray(random.getrandbits(8) for _ in range(4096))

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Length', len(binary_file) * 2)
            self.end_headers()
            self.wfile.write(binary_file)

        http_server.handler.do_GET = handler

        req = Request(Request.DOWNLOAD, 'GET', http_server.base_uri, {})

        with pytest.raises(InterruptedDownloadError):
            with http_server:
                send_request.download(req, self.session)

    def test_upload(self, http_server):
        binary_file = bytearray(random.getrandbits(8) for _ in range(4096))
        req = Request(Request.UPLOAD, 'PUT', http_server.base_uri, {})
        req.source = io.BytesIO(binary_file)

        def handler(self):
            content_length = int(self.headers.get('content-length'))
            assert content_length == len(binary_file)
            assert self.rfile.read(content_length) == binary_file
            self.send_response(204)
            self.end_headers()

        http_server.handler.do_PUT = handler
        with http_server:
            result = send_request.upload(req, self.session)
        assert result.get('code') is 204

    def test_request_with_http_error(self, http_server):
        url = '%s?code=%s&response=%s' % (http_server.base_uri, 404,
                                          '{"a":"b"}')
        req = Request(Request.JSON, 'GET', url, {})

        with pytest.raises(HTTPError) as exc_info:
            with http_server:
                send_request.json_request(req, self.session)
        assert exc_info.value.code == 404
        assert exc_info.value.response == {'a': "b"}

    def test_no_connection_error(self, http_server):
        req = Request(Request.JSON, 'GET', 'http://not-exist.example.com', {})
        with pytest.raises(ConnectionError):
            send_request.json_request(req, self.session)

    def test_request_timeout_error(self, http_server):
        def handler(self):
            self.send_response(204)
            import time
            time.sleep(1)
            pass

        http_server.handler.do_GET = handler
        req = Request(Request.JSON, 'GET', http_server.base_uri,
                      {'timeout': 0.05})
        with http_server:
            with pytest.raises(NetworkError):
                send_request.json_request(req, self.session)
