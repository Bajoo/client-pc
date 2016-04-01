# -*- coding: utf-8 -*-
import logging

from .. import promise
from ..common.i18n import N_
from ..network import json_request, download, upload
from ..network.errors import NetworkError
from ..network.errors import HTTPUnauthorizedError
from .user import User


_logger = logging.getLogger(__name__)

IDENTITY_API_URL = 'https://192.168.2.100'
STORAGE_API_URL = 'https://192.168.2.100:8080/v1'

CLIENT_ID = 'e2676e5d1fff42f7b32308e5eca3c36a'
CLIENT_SECRET = '<client-secret>'

TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token'])
REVOKE_TOKEN_URL = '/'.join([IDENTITY_API_URL, 'token', 'revoke'])


class InvalidDataError(NetworkError):
    def __init__(self, data):
        message = N_("The authentication server has returned invalid data.")
        super(InvalidDataError, self).__init__(None, message=message)
        self.data = data


class OAuth2Session(object):
    """Generic OAuth2 Session.

    Attributes:
        refresh_token
        access_token
        token_changed_callback (callable): A callback that can be assigned to
            be informed of token changes.
    """

    def __init__(self):
        self.refresh_token = None
        self.access_token = None
        self.token_changed_callback = None

    @classmethod
    def from_client_credentials(cls):
        """Instantiate a new client-only session.

        A client session is a session associated with no user. It's used to
        performs non-user related actions, as creating a new user.

        Returns:
            Promise<Session>
        """
        request_data = {
            u'grant_type': u'client_credentials'
        }
        return cls._send_auth_request(cls(), request_data)

    @classmethod
    def from_user_credentials(cls, username, password):
        """Instantiate a new user session from a couple username and password.

        Args:
            username (unicode): username credential
            password (unicode): password credential
        Returns:
            Promise<Session>
        """
        request_data = {
            u'username': username,
            u'password': password,
            u'grant_type': u'password'
        }
        return cls._send_auth_request(cls(), request_data)

    @classmethod
    def from_refresh_token(cls, refresh_token):
        """Instantiate a new user session from a refresh_token.

        Args:
            refresh_token: refresh token of a previous session.
        Returns:
            Promise<Session>
        """
        request_data = {
            u'refresh_token': refresh_token,
            u'grant_type': u'refresh_token'
        }
        return cls._send_auth_request(cls(), request_data)

    @staticmethod
    @promise.reduce_coroutine()
    def _send_auth_request(session, request_data):
        """Generic method to send authentication request."""
        auth = (CLIENT_ID, CLIENT_SECRET)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }

        response = yield json_request('POST', TOKEN_URL, auth=auth,
                                      headers=headers, data=request_data)
        content = response['content']

        try:
            session.access_token = content['access_token']
        except:
            raise InvalidDataError(content)
        session.refresh_token = content.get('refresh_token')
        session._notify_token_changed()

        yield session

    @promise.reduce_coroutine()
    def revoke(self):
        """Revoke all permissions granted by the session.

        The refresh_token and the access_token will both be revoked.
        The two token attributes are set to None immediately (ie, without
        waiting the revocation request).

        Returns:
            Future<None>: Resolve when the revocation is done.
        """
        auth = (CLIENT_ID, CLIENT_SECRET)
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
        data = {
            u'token': self.refresh_token
        }

        self.refresh_token = None
        self.access_token = None
        yield json_request('POST', REVOKE_TOKEN_URL,
                           auth=auth, headers=headers, data=data)
        yield None

    def _notify_token_changed(self):
        if self.token_changed_callback:
            self.token_changed_callback(self)


class Session(OAuth2Session):

    @classmethod
    def from_user_credentials(cls, email, password):
        """
        Create a new session using email & password.

        Returns:
            Future<Session>
        """
        password = User.hash_password(password)
        return super(Session, cls).from_user_credentials(email, password)

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

        if 'Authorization' in param_headers and self.access_token:
            param_headers['Authorization'] = \
                'Bearer ' + self.access_token
        else:
            # Add default headers params if not exist
            headers = {
                'Authorization': 'Bearer ' + self.access_token
            } if self.access_token else {}

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

            request_data = {
                u'refresh_token': self.refresh_token,
                u'grant_type': u'refresh_token'
            }
            yield self._send_auth_request(self, request_data)
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


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    session1 = Session.from_user_credentials('test+test_api@bajoo.fr',
                                             'test+test_api@bajoo.fr').result()
    session2 = Session.from_refresh_token(session1.refresh_token).result()

    try:
        # This should throw 404 error
        session1.disconnect().result()
    except Exception as e:
        _logger.error(e)

    # This should function correctly
    session2.disconnect().result()

    # Test retry on HTTPUnauthorizedError
    session1 = Session.from_user_credentials('test+test_api@bajoo.fr',
                                             'test+test_api@bajoo.fr').result()
    # Make the session expired
    session1.token[u'access_token'] = 'invalid_token'
    future = User.load(session1).then(
        lambda _user: _user.get_user_info().result())
    _logger.debug("User info: %s", future.result())
