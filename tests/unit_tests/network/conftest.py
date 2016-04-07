# -*- coding: utf-8 -*-

import pytest
from dummy_http_server import DummyHttpServer


@pytest.fixture
def http_server(request):
    """Create a ready to use local HTTP server.

    The fixture automatically closes the server at the end of the test.

    Returns:
        DummyHttpServer: the server instance. Contains a ``handler`` property,
            who is the base class used as request handler.
    """
    httpd = DummyHttpServer()
    request.addfinalizer(httpd.close)
    return httpd
