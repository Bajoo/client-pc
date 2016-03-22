# -*- coding: utf-8 -*-

from bajoo.promise import Deferred
from bajoo.network.errors import NetworkError
from bajoo.network.request import Request
from bajoo.network.status_table import StatusTable


class FakeChecker(object):
    def __init__(self):
        self.check_deferred = {}

    def check(self, url):
        df = Deferred()
        self.check_deferred[url] = df
        return df.promise

    def stop(self):
        pass


class TestStatusTable(object):

    def test_allow_requests_by_default(self):
        checker = FakeChecker()
        st = StatusTable(checker)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr')
        assert not st.reject_request(req)
        req2 = Request(Request.DOWNLOAD, 'GET', 'http://api.bajoo.fr')
        assert not st.reject_request(req2)

    def test_start_ping_on_network_error(self):
        checker = FakeChecker()
        st = StatusTable(checker)
        req = Request(Request.JSON, 'GET', 'http://api.bajoo.fr')

        error = NetworkError()
        st.update(req, error)
        for i in checker.check_deferred:
            print(i)
        assert 'http://api.bajoo.fr' in checker.check_deferred

    def test_start_ping_on_base_url(self):
        checker = FakeChecker()
        st = StatusTable(checker)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/path')
        error = NetworkError()
        st.update(req, error)
        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/alt_path')
        error = NetworkError()
        st.update(req, error)
        assert 'http://www.bajoo.fr' in checker.check_deferred
        assert len(checker.check_deferred) == 1

    def test_prevents_requests_when_network_is_down(self):
        checker = FakeChecker()
        st = StatusTable(checker)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/')

        assert not st.reject_request(req)

        error = NetworkError()
        st.update(req, error)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/')
        assert st.reject_request(req) == error

    def test_always_allow_ping_requests(self):
        checker = FakeChecker()
        st = StatusTable(checker)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/path')
        assert not st.reject_request(req)

        error = NetworkError()
        st.update(req, error)

        req = Request(Request.PING, 'GET', 'http://www.bajoo.fr/')
        assert not st.reject_request(req)

    def test_allow_requests_when_network_is_up(self):
        checker = FakeChecker()
        st = StatusTable(checker)

        req = Request(Request.JSON, 'GET', 'http://www.bajoo.fr/')
        assert not st.reject_request(req)

        error = NetworkError()
        st.update(req, error)
        assert st.reject_request(req) == error
        st.update(req)
        assert not st.reject_request(req)

    # TODO: callbacks !
