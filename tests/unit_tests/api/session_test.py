# -*- coding: utf-8 -*-

import collections
import pytest

import bajoo.api.session
from bajoo.api.session import Session, IDENTITY_API_URL, STORAGE_API_URL
from bajoo.api.user import User
from bajoo.network.errors import HTTPUnauthorizedError
from bajoo.promise import Deferred, Promise, TimeoutError


class MockTokenExpiredError(HTTPUnauthorizedError):
    def __init__(self):
        self.code = 401002
        self.reason = 'Token Expired'
        self.request = 'GET /path'
        self.response = {
            'code': 401002,
            'message': 'Token expired'
        }


class MockSessionFunctions(object):
    """Helpers for replacing functions of the Session module.

    the two methods 'on()' and 'async()' must be used once per request. They
    defines the responses returned by the mocked network module.

    Attributes:
        history (list of str): list of all requests made, in order they've
            been made. Each entry is the path.
    """

    def __init__(self, monkeypatch):
        self.history = []
        self._expected_requests = collections.defaultdict(list)
        monkeypatch.setattr(bajoo.api.session, 'json_request',
                            self._execute_identity_request)
        monkeypatch.setattr(bajoo.api.session, 'download',
                            self._execute_storage_request)
        monkeypatch.setattr(bajoo.api.session, 'upload',
                            self._execute_storage_request)

    @staticmethod
    def ok_response(content='CONTENT'):
        return {
            'code': 200,
            'headers': {},
            'content': content
        }

    @staticmethod
    def auth_response(access_token='ACCESS', refresh_token='REFRESH'):
        return {
            'code': 200,
            'headers': {},
            'content': {
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }

    def on(self, path, response):
        """Set response for the next request to "path"

        Order are executed in the same order as declared (fifo).
        """
        if isinstance(response, Exception):
            p = Promise.reject(response)
        else:
            p = Promise.resolve(response)
        self._expected_requests[path].append(p)

    def async(self, path):
        """Set async method for "path". """
        df = Deferred()
        self._expected_requests[path].append(df.promise)
        return df

    def _execute_storage_request(self, verb, url, *args, **kwargs):
        path = url[len(STORAGE_API_URL):]
        return self._execute_request(verb, path)

    def _execute_identity_request(self, verb, url, *args, **kwargs):
        path = url[len(IDENTITY_API_URL):]
        return self._execute_request(verb, path)

    def _execute_request(self, verb, path):
        self.history.append(path)
        try:
            return self._expected_requests[path].pop(0)
        except IndexError:
            assert False, "Unexpected request %s %s" % (verb, path)


class TestSession(object):

    def _auth_response(self):
        """Generic OK response for OAuth request."""
        return Promise.resolve({
            'code': 200,
            'headers': {},
            'content': {
                'access_token': 'ACCESS',
                'refresh_token': 'REFRESH'
            },
        })

    def _token_expired_response(self):
        """HTTP response 401 expired token error."""
        return Promise.reject(MockTokenExpiredError())

    def test_create_session_from_user_credentials(self, monkeypatch):
        context = {'called': False}

        def json_request(verb, url, auth=(), data={}, headers={}):
            assert context['called'] is False  # only 1 request allowed.
            assert verb is 'POST'
            assert len(auth) == 2  # There is auth credentials.
            assert data == {
                'grant_type': 'password',
                'username': "foo",
                'password': User.hash_password("bar")
            }
            return self._auth_response()

        monkeypatch.setattr(bajoo.api.session, 'json_request', json_request)

        promise = Session.from_user_credentials('foo', 'bar')
        session = promise.result(0.01)
        assert session.access_token == 'ACCESS'
        assert session.refresh_token == 'REFRESH'

    def test_create_session_from_client_credentials(self, monkeypatch):
        context = {'called': False}

        def json_request(verb, url, auth=(), data={}, headers={}):
            assert context['called'] is False  # only 1 request allowed.
            assert verb is 'POST'
            assert len(auth) == 2  # There is auth credentials.
            assert data == {'grant_type': 'client_credentials'}
            return self._auth_response()

        monkeypatch.setattr(bajoo.api.session, 'json_request', json_request)

        promise = Session.from_client_credentials()
        session = promise.result(0.01)
        assert session.access_token == 'ACCESS'
        assert session.refresh_token == 'REFRESH'

    def test_create_session_from_refresh_token(self, monkeypatch):
        context = {'called': False}

        def json_request(verb, url, auth=(), data={}, headers={}):
            assert context['called'] is False  # only 1 request allowed.
            assert verb is 'POST'
            assert len(auth) == 2  # There is auth credentials.
            assert data == {
                'grant_type': 'refresh_token',
                'refresh_token': 'OLD TOKEN'
            }
            return self._auth_response()

        monkeypatch.setattr(bajoo.api.session, 'json_request', json_request)

        promise = Session.from_refresh_token('OLD TOKEN')
        session = promise.result(0.01)
        assert session.access_token == 'ACCESS'
        assert session.refresh_token == 'REFRESH'

    def test_revoke_session(self, monkeypatch):
        def json_request(verb, url, data={}, **kwargs):
            assert data.get('token', None) == 'TOKEN'
            return Promise.resolve({
                'code': 204,
                'headers': {},
                'content': None
            })

        monkeypatch.setattr(bajoo.api.session, 'json_request', json_request)

        session = Session()
        session.refresh_token = 'TOKEN'
        p = session.revoke()
        assert session.refresh_token is None
        assert session.access_token is None
        assert p.result(0.001) is None

    def test_token_is_refreshed_when_it_expires(self, monkeypatch):
        """Test that the token is automatically refreshed if needed.

        The first DL request will fail with a '401' error.
        Then, the session should make a re-auth request, then eventually
        retry the DL.
        """
        network = MockSessionFunctions(monkeypatch)
        session = Session()
        session.access_token = 'EXPIRED_TOKEN'
        session.refresh_token = 'REFRESH_TOKEN'

        network.on('/path', MockTokenExpiredError())
        network.on('/token', network.auth_response())
        network.on('/path', network.ok_response('CONTENT'))

        p = session.download_storage_file('GET', '/path')
        assert p.result(0.001).get('content') == 'CONTENT'
        assert network.history == ['/path', '/token', '/path']

    def test_new_requests_wait_ongoing_token_refreshment(self, monkeypatch):
        """A request /req2 is started while an ongoing token refreshment.

        The second request must wait the result of the token refreshment,
        before being sent on the network.
        """
        network = MockSessionFunctions(monkeypatch)
        session = Session()

        network.on('/req1', MockTokenExpiredError())
        deferred_auth = network.async('/token')

        req1 = session.download_storage_file('GET', '/req1')

        # At this point, req1 is waiting for the /auth request to returns.
        assert network.history == ['/req1', '/token']

        req2 = session.download_storage_file('GET', '/req2')

        with pytest.raises(TimeoutError):
            req1.result(0.01)
        with pytest.raises(TimeoutError):
            req2.result(0)

        # /req2 hasn't been sent because it waits the token refreshment
        # initiated by /req1
        assert len(network.history) == 2

        network.on('/req2', network.ok_response())
        network.on('/req1', network.ok_response())

        # unlock the /auth response
        deferred_auth.resolve(network.auth_response())

        req1.result(0.01)
        req2.result(0.01)

        assert len(network.history) is 4
        assert sorted(network.history[-2:]) == ['/req1', '/req2']

    def test_concurrent_401_requests_performs_refresh_once(self, monkeypatch):
        """Several requests are concurrent and receive all the 401 error.

        Two requests are running when the token timeout occurs. The two
        requests will receive a 401 error.

        Only one refresh should be made. After the refreshment, both requests
        should be retried.
        """
        network = MockSessionFunctions(monkeypatch)
        session = Session()

        defer_req1 = network.async('/req1')
        defer_req2 = network.async('/req2')

        req1 = session.download_storage_file('GET', '/req1')
        req2 = session.download_storage_file('GET', '/req2')
        assert network.history == ['/req1', '/req2']
        # both requests are waiting the response.

        # returning the 401 on /req1 should trigger the token refreshment.
        defer_refresh = network.async('/token')
        defer_req1.reject(MockTokenExpiredError())

        # /req2 receive the 401, but the refreshment is ongoing.
        defer_req2.reject(MockTokenExpiredError())

        with pytest.raises(TimeoutError):
            req1.result(0.01)
        with pytest.raises(TimeoutError):
            req2.result(0)
        assert network.history == ['/req1', '/req2', '/token']

        # as soon as the token is refreshed, both req1 and req2 should be
        # retried.
        network.on('/req1', network.ok_response())
        network.on('/req2', network.ok_response())
        defer_refresh.resolve(network.auth_response('NEW_TOKEN'))

        assert req1.result(0.01)
        assert req2.result(0.01)

        assert len(network.history) == 5
        assert network.history.count('/token') == 1

    def test_slow_request_fails_as_token_has_changed(self, monkeypatch):
        """Requests should retry if the token has changed during its execution.

        Two requests are executed concurrently: /req1 and /slow. Both will
        receive the 401 error. /req1 will refresh the token as usual, then
        retry.

        The slow request will "catch" the 401 once the refresh as already
        happened. In this cas, the request should detect that the token has
        changed, then retry immediately without doing a new token refreshment.
        """
        network = MockSessionFunctions(monkeypatch)
        session = Session()

        defer_req1 = network.async('/req1')
        defer_slow_req = network.async('/slow')

        req1 = session.download_storage_file('GET', '/req1')
        slow_req = session.download_storage_file('GET', '/slow')
        assert network.history == ['/req1', '/slow']
        # both requests are waiting the response.

        # returning the 401 on /req1 should trigger the token refreshment.
        network.on('/token', network.auth_response('NEW_ACCESS'))
        network.on('/req1', network.ok_response())
        defer_req1.reject(MockTokenExpiredError())

        assert req1.result(0.01)
        with pytest.raises(TimeoutError):
            slow_req.result(0)

        # slow_req receives a 401, detect the token has changed, then retry
        # immediately.
        network.on('/slow', network.ok_response())
        defer_slow_req.reject(MockTokenExpiredError())

        assert slow_req.result(0.01)
        assert network.history == ['/req1', '/slow', '/token',
                                   '/req1', '/slow']
