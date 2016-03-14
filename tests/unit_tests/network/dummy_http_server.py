# -*- coding: utf-8 -*-

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:  # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import random
import threading


class DummyHttpServer(object):
    """HTTP server ready to use, for testing purpose.

    At creation, the server starts listening on a random port. The requests
    must be proceeded manually, by calling handle_request() once per request.
    When the server is no more used, it must be closed by calling close().

    The easiest way to use this server is two prepare all custom handlers, them
    use the instance as a context manager. The context manager will handle all
    requests, until the context is closed:

        http_server = DummyHttpServer()

        # ... set all handler
        http_server.handler.do_GET = my_handler;
        with http_server:
            # make requests to http_server.uri
        http_server.close()

    Attributes:
        handler (class BaseHTTPRequestHandler): Handler class used by the
            server.
        base_uri (str): Base URI (with leading slash).
    """

    def __init__(self):

        self._server = None
        self._thread = None

        # A new class is defined for each call, so the test functions can set
        # new methods (like do_GET) without interfering with others instances.
        class Handler(BaseHTTPRequestHandler):
            pass

        # Try 5 times on different ports to find one who is unused.
        attempts = 0
        while self._server is None:
            try:
                port = random.randint(1025, 65500)
                self._server = HTTPServer(('localhost', port), Handler)
            except (IOError, OSError):
                attempts += 1
                if attempts > 5:
                    raise

        self._server.timeout = 1
        self.handler = Handler
        self.base_uri = 'http://localhost:%s/' % self._server.server_port

    def handle_request(self):
        self._server.handle_request()

    def close(self):
        self._server.server_close()

    def __enter__(self):
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._server.shutdown()
        self._thread.join()
        self._thread = None
