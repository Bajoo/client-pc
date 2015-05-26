# -*- coding: utf8 -*-

import random

import pytest


try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:  # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import bajoo.network


class TestNetwork(object):
    """Test of the bajoo.network module"""

    @pytest.fixture
    def http_server(self, request):
        """Instantiate a basic HTTP server on a random port.

        Create an instance of HTTPServer. The server listen only to
        localhost and takes the first random port who is unused.
        Note that it does not automatically process requests. To process a
        pending request, use the ``handle_request`` method.

        The default behavior is to respond a 503 error on all requests. To
        catch and respond to requests, the ``do_*`` methods of the handler
        must be set. The Handler class is available in the server instance.

        The fixture automatically closes the server at the end of the test.

        Returns:
            HTTPBase: the server instance. Contains a ``handler`` property,
                who is the base class used as request handler.
        """

        # A new class is defined for each call, so the test functions can set
        # new methods (like do_GET) without interfering with others instances.
        class Handler(BaseHTTPRequestHandler):
            pass

        # Try 5 times on different ports to find one who is unused.
        attempts = 0
        while True:
            try:
                port = random.randint(1025, 65500)
                httpd = HTTPServer(('localhost', port), Handler)
                break
            except Exception:
                attempts += 1
                if attempts > 5:
                    raise

        httpd.handler = Handler
        request.addfinalizer(httpd.server_close)

        return httpd

    def test_json_request(self, http_server):
        """Make a simple JSON requests with code 200 OK."""

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"foo":"bar"}')

        http_server.handler.do_GET = handler
        f = bajoo.network.json_request('GET', 'http://localhost:%s/' %
                                       http_server.server_port)
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
        f = bajoo.network.json_request('GET', 'http://localhost:%s/' %
                                       http_server.server_port)
        http_server.handle_request()

        result = f.result(1)
        assert result.get('code') is 204
        assert result.get('content') is None

    @pytest.mark.xfail()
    def test_request_bad_server(self):
        """Make a download request to an unavailable server.

        The request should raise an exception.
        """

        f = bajoo.network.download('GET', 'http://example.not_exists/')

        with pytest.raises(bajoo.network.errors.ConnectionError):
            f.result()

    @pytest.mark.xfail()
    def test_request_timeout_server(self, http_server):
        """Make a download request to a server who does not respond.

        The target server accept the connexion, but don't send any data.
        The future should throw an exception after the timeout expires.
        """
        f = bajoo.network.download('GET', 'http://localhost:%s/' %
                                   http_server.server_port)

        with pytest.raises(bajoo.network.errors.ConnectTimeoutError):
            f.result()

    def test_download_empty_file(self, http_server):
        """Download a file of length 0."""

        def handler(self):
            self.send_response(200)
            self.send_header('Content-Length', 0)
            self.end_headers()

        http_server.handler.do_GET = handler
        f = bajoo.network.download('GET', 'http://localhost:%s/' %
                                   http_server.server_port)
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
        f = bajoo.network.download('GET', 'http://localhost:%s/' %
                                   http_server.server_port)
        http_server.handle_request()
        result = f.result(1)
        assert result.get('code') is 200
        result_file = result.get('content')
        assert result_file.read() == file_content
