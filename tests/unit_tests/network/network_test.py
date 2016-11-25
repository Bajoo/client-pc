# -*- coding: utf-8 -*-

from io import BytesIO
import pkg_resources

import pytest

import bajoo.network


class TestNetwork(object):
    """Test of the bajoo.network module"""

    def setup(self):
        self._context = bajoo.network.Context()
        self._context.start()

    def teardown(self):
        self._context.stop()

    def test_json_request(self, http_server):
        """Make a simple JSON requests with code 200 OK."""

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"foo":"bar"}')

        http_server.handler.do_GET = handler
        f = bajoo.network.json_request('GET', http_server.base_uri)
        http_server.handle_request()

        result = f.result(1)
        assert result.get('code') is 200
        assert 'foo' in result.get('content')
        assert result.get('content').get('foo') == 'bar'

    def test_json_request_204(self, http_server):
        """Make a JSON requests receiving a "204 No Content" response.

        The request should return a valid result object, with an empty content
        of value ``None``.
        """

        def handler(self):
            self.send_response(204)
            self.end_headers()

        http_server.handler.do_GET = handler
        f = bajoo.network.json_request('GET', http_server.base_uri)
        http_server.handle_request()

        result = f.result(1)
        assert result.get('code') is 204
        assert result.get('content') is None

    @pytest.mark.skipif(not pytest.config.getvalue('slowtest'),
                        reason='slow test')
    def test_request_bad_server(self):
        """Make a download request to an unavailable server.

        The request should raise an exception.
        """

        f = bajoo.network.download('GET', 'http://example.not_exists/')

        with pytest.raises(bajoo.network.errors.ConnectionError):
            f.result(10)

    def test_download_empty_file(self, http_server):
        """Download a file of length 0."""

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Length', 0)
            self.end_headers()

        http_server.handler.do_GET = handler
        f = bajoo.network.download('GET', http_server.base_uri)
        http_server.handle_request()
        result = f.result(1)
        assert result.get('code') is 200
        result_file = result.get('content')
        assert result_file.read() == b''

    def test_download_small_file(self, http_server):
        """Download a small file."""

        file_content = b"""Content of a small file
        Second line.
        Another line.
        """

        def handler(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(file_content)

        http_server.handler.do_GET = handler
        f = bajoo.network.download('GET', http_server.base_uri)
        http_server.handle_request()
        result = f.result(1)
        assert result.get('code') is 200
        result_file = result.get('content')
        assert result_file.read() == file_content

    def test_interrupted_requests(self, http_server):
        """Make a download request to a server who send truncated content.

        The target server announce a 25 bytes response, but returns less than
        that. It can happens when the HTTP connexion is lost in the middle of a
        download.
        The future should raise an exception.
        """

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Length', 25)
            self.end_headers()
            self.wfile.write(b'partial response')

        http_server.handler.do_GET = handler
        f = bajoo.network.download('GET', http_server.base_uri)
        http_server.handle_request()
        with pytest.raises(bajoo.network.errors.InterruptedDownloadError):
            f.result(1)

    def test_upload_empty_file(self, http_server):
        """Upload an empty file from its path.

        The server must receive an empty file.
        """

        def handler(self):
            assert 'content-length' not in self.headers or \
                int(self.headers.get('content-length')) is 0
            self.send_response(204)
            self.end_headers()

        http_server.handler.do_PUT = handler

        empty_file_path = pkg_resources.resource_filename(
            __name__, "../../resources/empty.txt")
        f = bajoo.network.upload('PUT', http_server.base_uri, empty_file_path)
        http_server.handle_request()
        f.result(1)

    def test_upload_small_file(self, http_server):
        """Upload a small file, using a stream.

        The server must receive the exact file.
        """

        file_content = b"""Content of the small file
        ... ... ...
        Third line.
        """

        def handler(self):
            content_length = int(self.headers.get('content-length'))
            assert content_length is len(file_content)
            assert self.rfile.read(content_length) == file_content
            self.send_response(204)
            self.end_headers()

        http_server.handler.do_PUT = handler

        f = bajoo.network.upload('PUT', http_server.base_uri,
                                 BytesIO(file_content))
        http_server.handle_request()
        f.result(1)
