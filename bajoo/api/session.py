# -*- coding: utf-8 -*-
import logging
from hashlib import sha256

from ..network import json_request


_logger = logging.getLogger(__name__)

IDENTITY_API_URL = 'https://192.168.2.100'
STORAGE_API_URL = 'https://192.168.2.100:8080'

CLIENT_ID = 'e2676e5d1fff42f7b32308e5eca3c36a'
CLIENT_SECRET = '<client-secret>'

TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token'])
REVOKE_TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token', 'revoke'])


class BajooOAuth2Session(object):
    """Represent a OAuth2 session for connecting to Bajoo server."""

    def __init__(self):
        self.token = None

    def _prepare_request(self):
        """
        Create common fields to send with the request.

        Returns (tuple): (headers, data)
        """
        auth = (CLIENT_ID, CLIENT_SECRET)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }

        return auth, headers

    def fetch_token(self, token_url, email, password):
        """
        Fetch a new access_token using email & password.

        Args:
            token_url (str): the url to which the request will be sent
            email (str): user email
            password (str): user (plain) password

        Returns:
            Future<None>
        """

        # TODO: the hash password function will be moved to the user class
        hash_password = sha256(password.encode('utf-8')).hexdigest()

        # Send request to token url
        auth, headers = self._prepare_request()
        data = {
            u'username': email,
            u'password': hash_password,
            u'grant_type': u'password'
        }

        response_future = json_request('POST', token_url,
                                       auth=auth, headers=headers, data=data,
                                       # disable temporarily
                                       # certificate verifying
                                       verify=False)

        def _on_request_result(response):
            # Analyze response and save the tokens
            if response and response.get('code') == 200:
                self.token = response.get('content')
                _logger.info('Token fetched = %s', self.token)

        return response_future.then(_on_request_result)

    def refresh_token(self, token_url, refresh_token):
        """
        Fetch a new token using the refresh_token.

        Args:
            token_url (str): the url to which the request will be sent
            refresh_token (str): the existing refresh token

        Returns:
            Future<None>
        """
        auth, headers = self._prepare_request()
        data = {
            u'refresh_token': refresh_token,
            u'grant_type': u'refresh_token'
        }

        request_future = json_request('POST', token_url,
                                      auth=auth, headers=headers, data=data,
                                      # disable temporarily
                                      # certificate verifying
                                      verify=False)

        def _on_request_result(response):
            # Analyze response and save the tokens
            if response and response.get('code') == 200:
                self.token = response.get('content')
                _logger.info('Token refreshed = %s', self.token)

        return request_future.then(_on_request_result)

    def is_authorized(self):
        """
        A boolean value indicating whether this session has an
        OAuth2 access token.

        Returns:
            True if this session has an access token, otherwise False.
        """
        return bool(self.token.get('access_token', None))


class Session(BajooOAuth2Session):
    def __init__(self):
        BajooOAuth2Session.__init__(self)

    @staticmethod
    def create_session(email, password):
        """
        Create a new session using email & password.

        Returns:
            Future<Session>
        """
        new_session = Session()
        return new_session.fetch_token(TOKEN_URL, email, password) \
            .then(lambda __: new_session)

    @staticmethod
    def load_session(refresh_token):
        """
        Restore an old session using refresh_token.

        Returns:
            Future<Session>
        """
        new_session = Session()
        return new_session.refresh_token(TOKEN_URL, refresh_token) \
            .then(lambda __: new_session)

    def get_refresh_token(self):
        """
        Get the refresh_token.

        Returns:
            (str) The refresh token
        """
        if self.token:
            return self.token.get('refresh_token', None)

        return None

    def revoke_refresh_token(self):
        """
        Revoke the refresh_token (and implicitly the access_token)

        Returns:
            Future<None>
        """
        auth, headers = self._prepare_request()
        data = {
            u'token': self.token.get('refresh_token', '')
        }

        request_future = json_request('POST', REVOKE_TOKEN_URL,
                                      auth=auth, headers=headers, data=data,
                                      # disable temporarily
                                      # certificate verifying
                                      verify=False)

        def _on_request_result(response):
            # Analyze response and save the tokens
            if response and response.get('code') == 200:
                _logger.debug('Token revoked successfully')

        return request_future.then(_on_request_result)

    def disconnect(self):
        """
        Disconnect the session.

        Returns:
            Future<None>
        """

        def _on_token_revoked(result):
            self.token = None

        return self.revoke_refresh_token().then(_on_token_revoked)


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    session1 = Session.create_session('stran+51@bajoo.fr',
                                      'stran+51@bajoo.fr').result()
    session2 = Session.load_session(session1.get_refresh_token()).result()

    try:
        # This should throw 404 error
        session1.disconnect().result()
    except Exception as e:
        _logger.error(e)

    # This should function correctly
    session2.disconnect().result()
