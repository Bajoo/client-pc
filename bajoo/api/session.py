# -*- coding: utf-8 -*-

import logging
import threading
try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

from .. import network
from .. import promise
from ..common.i18n import N_
from ..common.strings import to_str
from ..network.errors import NetworkError
from ..network.errors import HTTPUnauthorizedError
from ..promise import Deferred, Promise
from .user import User


_logger = logging.getLogger(__name__)

IDENTITY_API_URL = 'https://beta.bajoo.fr'
STORAGE_API_URL = 'https://storage.bajoo.fr/v1'

CLIENT_ID = '2ba50c9b4ca145fe981797078cdea977'
CLIENT_SECRET = '9e2f765a119b415e97612d0f7c28c0b2'

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

        # Lock used when acceding the access_token, after initialization.
        # It prevents race condition.
        # It must be locked only on instant operations.
        self._lock = threading.Lock()

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

        response = yield network.json_request('POST', TOKEN_URL, auth=auth,
                                              headers=headers,
                                              data=request_data)
        content = response['content']

        try:
            session.access_token = content['access_token']
        except:
            raise InvalidDataError(content)
        with session._lock:
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
        yield network.json_request('POST', REVOKE_TOKEN_URL,
                                   auth=auth, headers=headers, data=data)
        yield None

    def _notify_token_changed(self):
        if self.token_changed_callback:
            self.token_changed_callback(self)


class Session(OAuth2Session):

    def __init__(self):
        super(Session, self).__init__()

        # The flag is raised (set to True) by default. It's set to False when
        # there is a refreshment.
        self._token_refreshment_event = threading.Event()
        self._token_refreshment_event.set()

        # Deferred used for async waiting of token operations.
        # Must be protected by self._lock
        self._defer_retry = None

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
                            headers=None, **params):
        """Send a request to a Bajoo server, using OAuth2 authentication.

        Args:
            api_url (str): the api url (storage or identity)
            verb (str): the verb of the RESTful function
            url_path (str): part of the url after the host address,
                e.g. /user, /storage, etc.
            network_fun (fun): the network function to execute (download,
                upload, json_request, ...)
            headers (dict, optional): HTTP headers, transmitted to network_fun
            **params (dict): optional parameters, transmitted to network_fun
        Returns:
            Promise<dict>: the promise returned by the network function.
        """

        # Force waiting if there is an operation on token.
        yield self._async_wait_for_refreshment()

        with self._lock:
            access_token = self.access_token

        if not headers:
            headers = {}
        headers['Authorization'] = 'Bearer %s' % access_token
        url = api_url + quote(to_str(url_path))

        try:
            yield network_fun(verb, url, headers=headers, **params)
        except HTTPUnauthorizedError as error:
            # Refresh the token and retry if HTTPUnauthorizedError

            # If the response has a code, it's a bajoo-api response. Otherwise,
            # it's a storage server response, and we don't have details on the
            # 401 reason.
            if isinstance(error.response, dict):
                if error.response.get('code', 401002) != 401002:
                    raise  # not a session expired error

            need_refresh_token = False
            with self._lock:
                if self.access_token == access_token:
                    if self._token_refreshment_event.is_set():
                        # We keep the refreshment event to False until the auth
                        # request returns, to force subsequent requests to wait
                        # the token refreshment.
                        self._token_refreshment_event.clear()
                        need_refresh_token = True

            if need_refresh_token:
                # It's the first request to catch the 401 error.

                request_data = {
                    u'refresh_token': self.refresh_token,
                    u'grant_type': u'refresh_token'
                }

                try:
                    yield self._send_auth_request(self, request_data)
                finally:
                    self._token_refreshment_event.set()
            else:
                # At this point, we are in a network thread (the one which has
                # executed network_fin()). We must not block the current
                # thread. Using self._async_wait_for_refreshment() ensures the
                # current thread will not block.
                yield self._async_wait_for_refreshment()

            # Token refreshed, we retry.
            yield self._send_bajoo_request(api_url, verb, url_path,
                                           network_fun, headers, **params)

    def _async_wait_for_refreshment(self):
        """Wait for the token refreshment to finish.

        If there is no token refreshment, the promise returned resolves
        immediately (in the caller thread).

        However, if there is a token refreshment ongoing, a dedicated thread is
        used, and the promise will resolve at this moment.

        Returns:
            Promise (None): resolved as soon as there is no token refreshment.
        """
        with self._lock:
            if self._token_refreshment_event.is_set():
                return Promise.resolve(None)  # No need no wait.

            if self._defer_retry:
                start_new_thread = False
                defer_retry = self._defer_retry  # reuse waiting thread
            else:
                # new waiting thread.
                self._defer_retry = Deferred()
                defer_retry = self._defer_retry
                start_new_thread = True
        if start_new_thread:
            t = threading.Thread(target=self._wait_for_refreshment,
                                 args=(defer_retry,),
                                 name='Token refreshment waiting')
            t.daemon = True
            t.start()
        return defer_retry.promise

    def _wait_for_refreshment(self, deferred):
        self._token_refreshment_event.wait()
        with self._lock:
            self._defer_retry = None
        deferred.resolve(None)

    def update(self, access_token, refresh_token):
        """Manually update the session.

        It's useful in case of change provoked by an external action, like a
        password change.

        Args:
            access_token
            refresh_token
        """
        with self._lock:
            self.access_token = access_token
            self.refresh_token = refresh_token
            self._notify_token_changed()

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
                                        network.json_request, **params)

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
                                        network.json_request, **params)

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
                                        network.download, **params)

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
                                        network.upload, **params)


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
