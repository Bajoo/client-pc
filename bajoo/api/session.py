# -*- coding: utf-8 -*-
import logging
from hashlib import sha256

from ..network import json_request


_logger = logging.getLogger(__name__)

IDENTITY_API_URL = 'https://192.168.2.100'
STORAGE_API_URL = 'https://192.168.2.100:8080'

CLIENT_ID = 'e2676e5d1fff42f7b32308e5eca3c36a'
CLIENT_SECRET = '<client-secret>'


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

        future = json_request('POST', token_url,
                              auth=auth, headers=headers, data=data,
                              # disable temporarily certificate verifying
                              verify=False)
        response = future.result()

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            self.token = response.get('content')
            _logger.info('Token fetched = %s', self.token)

    def refresh_token(self, token_url, refresh_token):
        """
        Fetch a new token using the refresh_token.

        Args:
            token_url (str): the url to which the request will be sent
            refresh_token (str): the existing refresh token

        Returns:
            Future<None>
        """
        # Send request to token url
        auth, headers = self._prepare_request()
        data = {
            u'refresh_token': refresh_token,
            u'grant_type': u'refresh_token'
        }

        future = json_request('POST', token_url,
                              auth=auth, headers=headers, data=data,
                              # disable temporarily certificate verifying
                              verify=False)
        response = future.result()

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            self.token = response.get('content')
            _logger.info('Token refreshed = %s', self.token)

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
        new_session.fetch_token(IDENTITY_API_URL + '/token', email, password)

        return new_session

    @staticmethod
    def load_session(refresh_token):
        """
        Restore an old session using refresh_token.

        Returns:
            Future<Session>
        """
        new_session = Session()
        new_session.refresh_token(IDENTITY_API_URL + '/token', refresh_token)

        return new_session

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
        pass

    def disconnect(self):
        """
        Disconnect the session.

        Returns:
            Future<None>
        """
        pass


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    session = BajooOAuth2Session()
    session.fetch_token(token_url=IDENTITY_API_URL + '/token',
                        email='stran+50@bajoo.fr',
                        password='stran+50@bajoo.fr')
    _logger.info('Session authorized = %s', session.is_authorized())
    session.refresh_token(token_url=IDENTITY_API_URL + '/token',
                          refresh_token=session.token.get('refresh_token', ''))
