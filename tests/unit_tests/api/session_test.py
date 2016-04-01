# -*- coding: utf-8 -*-

import bajoo.api.session
from bajoo.api.session import Session
from bajoo.api.user import User
from bajoo.promise import Promise


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
