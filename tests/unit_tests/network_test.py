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

        r = f.result(1)
        assert 'foo' in r
        assert r.get('foo') == 'bar'

    @pytest.mark.xfail()
    def test_json_request_204(self, http_server):
        """Make a JSON requests receiving a "204 No Content" response."""

        def handler(self):
            self.send_response(204)
            self.end_headers()

        http_server.handler.do_GET = handler
        f = bajoo.network.json_request('GET', 'http://localhost:%s/' %
                                       http_server.server_port)
        http_server.handle_request()

        assert f.result(1) is None
