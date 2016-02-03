# -*- coding: utf-8 -*-
import logging

from .. import promise
from ..network import json_request, download, upload
from ..network.errors import HTTPUnauthorizedError
from .user import User


_logger = logging.getLogger(__name__)

IDENTITY_API_URL = 'https://beta.bajoo.fr'
STORAGE_API_URL = 'https://storage.bajoo.fr/v1'

# These credentials are valid, but are intended for test purpose only.
# They can be revoked at any moment. If you want to develop your own client,
# either for distributing it or for your personal use, please contact us at
# <support-en@bajoo.fr> and we will be happy to provide you some credentials.
CLIENT_ID = '24e1aba5d72046dd8db4410176613698'
CLIENT_SECRET = '4f2c73941fda45eaa5e72a0ade8e7b80'

TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token'])
REVOKE_TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token', 'revoke'])


class BajooOAuth2Session(object):
    """Represent a OAuth2 session for connecting to Bajoo server."""

    def __init__(self):
        self.token = None
        self.token_changed_callback = None

    def _notify_token_changed(self):
        if self.token_changed_callback and self.token:
            self.token_changed_callback(self.token.get('refresh_token', None))

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

    @promise.reduce_coroutine()
    def fetch_client_token(self, token_url=None):
        """
        Fetch a new client token to use for non-specific-user request.

        Args:
            token_url (str): the url to which the request will be sent

        Returns:
            Future<None>
        """
        token_url = token_url or TOKEN_URL
        auth, headers = self._prepare_request()
        data = {
            u'grant_type': u'client_credentials'
        }

        response = yield json_request('POST', token_url, auth=auth,
                                      headers=headers, data=data)

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            self.token = response.get('content')
            self._notify_token_changed()

        yield None

    @promise.reduce_coroutine()
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

        # Send request to token url
        token_url = token_url or TOKEN_URL
        auth, headers = self._prepare_request()
        data = {
            u'username': email,
            u'password': User.hash_password(password),
            u'grant_type': u'password'
        }

        response = yield json_request('POST', token_url, auth=auth,
                                      headers=headers, data=data)

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            self.token = response.get('content')
            self._notify_token_changed()
            _logger.info('Token fetched = %s', self.token)

        yield None

    @promise.reduce_coroutine()
    def refresh_token(self, token_url=None, refresh_token=None):
        """
        Fetch a new token using the refresh_token.

        Args:
            token_url (str, optional): the url to which the request will be
                sent. TOKEN_URL by default.
            refresh_token (str, optional): the existing refresh token.
                If not provided, the current token.refresh_token will be used.

        Returns:
            Future<None>
        """
        token_url = token_url or TOKEN_URL
        refresh_token = refresh_token or self.token.get('refresh_token', None)

        if not refresh_token:
            raise ValueError("Missing refresh token")

        auth, headers = self._prepare_request()
        data = {
            u'refresh_token': refresh_token,
            u'grant_type': u'refresh_token'
        }

        response = yield json_request('POST', token_url, auth=auth,
                                      headers=headers, data=data)

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            self.token = response.get('content')
            self._notify_token_changed()
            _logger.info('Token refreshed = %s', self.token)

        yield None

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

    @promise.reduce_coroutine()
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

        response = yield json_request('POST', REVOKE_TOKEN_URL,
                                      auth=auth, headers=headers, data=data)

        # Analyze response and save the tokens
        if response and response.get('code') == 200:
            _logger.debug('Token revoked successfully')

        yield None

    @promise.reduce_coroutine()
    def _send_bajoo_request(self, api_url, verb, url_path, network_fun,
                            **params):
        """
        Send a json request to Bajoo server.
        The url will be resolved according to the `request_type`

        Args:
            api_url (str): the api url (storage or identity)
            verb (str): the verb of the RESTful function
            url_path (str): part of the url after the host address,
                e.g. /user, /storage, etc.
            network_fun (fun): the network function to execute (download,
                upload, json_request, ...)

        Returns (Future<dict>): the future returned by json_request
        """
        # Replace the old token if neccessary
        param_headers = params.get('headers', {})

        if 'Authorization' in param_headers and self.token:
            param_headers['Authorization'] = \
                'Bearer ' + self.token.get('access_token', '')
        else:
            # Add default headers params if not exist
            headers = {
                'Authorization': 'Bearer ' + self.token.get('access_token', '')
            } if self.token else {}

            headers.update(param_headers)
            params['headers'] = headers

        url = api_url + url_path

        try:
            yield network_fun(verb, url, **params)
        except HTTPUnauthorizedError as error:
            # Refresh the token and retry if HTTPUnauthorizedError
            try:
                error_code = error.response.get('code', 401)
            except AttributeError:  # there is not response
                raise error

            if error_code != 401002:  # session expired error
                raise

            yield self.refresh_token()
            yield network_fun(verb, url, **params)

    def send_api_request(self, verb, url_path, **params):
        """
        Send a json request to Bajoo API

        Args:
            verb (str): the verb of the RESTful function
            url_path (str): part of the url after the host address,
                e.g. /user, /storage, etc.

        Returns (Future<dict>): the future returned by json_request
        """
        return self._send_bajoo_request(IDENTITY_API_URL, verb, url_path,
                                        json_request, **params)

    def send_storage_request(self, verb, url_path, **params):
        """
        Send a json request to Swift API

        Args:
            verb (str): the verb of the RESTful function
            url_path (str): part of the url after the host address,
                e.g. /user, /storage, etc.

        Returns (Future<dict>): the future returned by json_request
        """
        return self._send_bajoo_request(STORAGE_API_URL, verb, url_path,
                                        json_request, **params)

    def download_storage_file(self, verb, url_path, **params):
        """
        Send a download request to Swift API

        Args:
            verb (str): the verb of the RESTful function
            url_path (str): part of the url after the host address,
                e.g. /keys/test@bajoo.fr.key, /storages/sample.txt, etc.

        Returns (Future<TemporaryFile>):
            the future returned by network.download
        """

        return self._send_bajoo_request(STORAGE_API_URL, verb, url_path,
                                        download, **params)

    def upload_storage_file(self, verb, url_path, source, **params):
        """Upload a file into the storage

        Note: if a file-like object is passed as source, it will be
        automatically closed after the upload.

        Args:
            verb (str): HTTP verb
            url_path (str): URL of the for '/storage/%id/%filename'
            source (str / File-like): path of the file to upload (if type is
                str), or file content to upload.
            **params (dict): additional parameters passed to `network.upload`.
        """
        params['source'] = source
        return self._send_bajoo_request(STORAGE_API_URL, verb, url_path,
                                        upload, **params)

    @promise.reduce_coroutine()
    def disconnect(self):
        """
        Disconnect the session.

        Returns:
            Future<None>
        """

        yield self.revoke_refresh_token()
        self.token = None

        yield None

if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    session1 = Session.create_session('stran+test_api@bajoo.fr',
                                      'stran+test_api@bajoo.fr').result()
    session2 = Session.load_session(session1.get_refresh_token()).result()

    try:
        # This should throw 404 error
        session1.disconnect().result()
    except Exception as e:
        _logger.error(e)

    # This should function correctly
    session2.disconnect().result()

    # Test retry on HTTPUnauthorizedError
    session1 = Session.create_session('stran+test_api@bajoo.fr',
                                      'stran+test_api@bajoo.fr').result()
    # Make the session expired
    session1.token[u'access_token'] = 'invalid_token'
    future = User.load(session1).then(
        lambda _user: _user.get_user_info().result())
    _logger.debug("User info: %s", future.result())
