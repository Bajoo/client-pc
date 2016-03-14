# -*- coding: utf-8 -*-

import io
import random

import pytest

from bajoo.network import send_request
from bajoo.network.request import Request


class TestSendRequest(object):

    def test_json_request(self, http_server):

        url = '%s?response=%s' % (http_server.base_uri, '{"foo":"bar"}')
        req = Request(Request.JSON, 'GET', url, {})

        with http_server:
            result = send_request.json_request(req)

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
            result = send_request.download(req)

        assert result.get('code') is 200

        buffer = b''
        with result.get('content') as dl_file:
            buffer += dl_file.read()
        assert buffer == binary_file

    @pytest.mark.xfail(reason='Content-length check is not implemented')
    def test_download_interrupted(self, http_server):
        binary_file = bytearray(random.getrandbits(8) for _ in range(4096))

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Length', len(binary_file) * 2)
            self.end_headers()
            self.wfile.write(binary_file)

        http_server.handler.do_GET = handler

        req = Request(Request.DOWNLOAD, 'GET', http_server.base_uri, {})

        with pytest.raises(Exception):  # Exception: incomplete download ...
            with http_server:
                send_request.download(req)

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
            result = send_request.upload(req)
        assert result.get('code') is 204
