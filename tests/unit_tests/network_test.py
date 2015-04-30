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

        Create an instance of HTTPServer, who respond to GET requests with a
        small JSON object: ``{"foo":"bar"}``. The server listen only to
        localhost and takes the first random port who is unused.
        Note that it does not automatically process requests. To process a
        pending request, use the ``handle_request`` method.

        The fixture automatically closes the server at the end of the test.

        Returns:
            (HTTPBase, int): A tuple containing the server instance and the
                port number used.
        """
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"foo":"bar"}')

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

        request.addfinalizer(httpd.server_close)

        return httpd, port

    def test_json_request(self, http_server):
        """Make a simple JSON requests with code 200 OK."""

        httpd, port = http_server

        f = bajoo.network.json_request('GET', 'http://localhost:%s/' % port)

        httpd.handle_request()

        r = f.result(1)
        assert 'foo' in r
        assert r.get('foo') == 'bar'
