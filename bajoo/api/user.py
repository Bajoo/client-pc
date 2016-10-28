# -*- coding: utf-8 -*-
import logging
from hashlib import sha256

from ..common import config
from ..common import i18n
from ..common.strings import ensure_unicode
from ..network.errors import HTTPNotFoundError
from .. import encryption
from ..encryption import AsymmetricKey
from ..promise import Promise, reduce_coroutine


_logger = logging.getLogger(__name__)


class User(object):
    """
    This class represent a Bajoo user, which treats the requests relating
    to the user account.
    """
    KEY_URL_FORMAT = '/keys/%s.key'
    PUBLIC_KEY_URL_FORMAT = '/keys/%s.key.pub'

    def __init__(self, name="", session=None):
        self.name = name
        self._session = session

    @staticmethod
    @reduce_coroutine()
    def create(email, password, lang=None):
        """
        Create a new user using email & password.

        Args:
            email (unicode): email of the new account
            password (unicode): password of the new account
            lang (str, optional): two-character language code, used to set the
                default language for the new account. Default to 'en'.
        Returns:
            Promise<None>
        """
        from .session import Session

        password = ensure_unicode(password)
        email = ensure_unicode(email)

        hashed_password = User.hash_password(password)
        session = yield Session.from_client_credentials()

        yield session.send_api_request('POST', '/users', data={
            u'email': email,
            u'password': hashed_password,
            u'lang': lang or i18n.get_lang()
        })
        yield None

    @staticmethod
    @reduce_coroutine()
    def load(session):
        """Load the User owner of an existing session.

        Note: by default, the data associated to this class are not loaded.
        Before using it, you should call `get_user_info()`
        It include s`self.name`

        Args:
            session (bajoo.api.Session): an authorized session

        Returns:
            Promise<User>
        """
        if not session:
            raise ValueError("Empty or null session")

        yield User(session=session)

    @staticmethod
    def hash_password(password):
        """Convert a password to a hash usable by the Bajoo API"""
        return sha256(password.encode('utf-8')).hexdigest()

    @reduce_coroutine()
    def get_quota(self):
        """
        Returns:
            Promise<(int, int)>: used & total storage space (in bytes).
        """
        response = yield self._session.send_storage_request('GET', '/quota')
        content = response['content']
        yield int(content.get('used_space', 0)), int(content.get('allowed', 0))

    @reduce_coroutine()
    def get_user_info(self):
        """
        Get user's public profile and load infos in this class.

        returns:
            Promise<dict>: user infos.
        """

        response = yield self._session.send_api_request('GET', '/user')
        content = response.get('content', {})
        self.name = content.get('email', '')

        # Migration code: the lang defined server-side is unreliable if
        # lang_unset is true (due to old client sending bad values).
        # In this case, we update the lang.
        if content.get('lang_unset'):
            lang = config.get('lang') or i18n.get_lang()

            if lang:
                _logger.info('Set lang account to %s', lang)
                response = yield self._session.send_api_request(
                    'PATCH', '/user', data={u'lang': lang})
                content = response.get('content', {})

        yield content

    def change_password(self, old_password, new_password):
        """
        Change current user password

        Arguments:
            old_password (str): current password in plain text
            new_password (str): new password in plain text

        Returns:
            Promise<None>
        """
        hashed_old_password = self.hash_password(old_password)
        hashed_new_password = self.hash_password(new_password)
        data = {'password': hashed_old_password,
                'new_password': hashed_new_password}

        # TODO: analyze result & handle error
        return self._session.send_api_request(
            'PATCH', '/user', data=data)

    @reduce_coroutine()
    def delete_account(self, password):
        """
        Remove current account from Bajoo.

        Args:
            password (str): current password in plain text

        Returns:
            Promise<None>
        """
        yield self._remove_encryption_key()
        yield self._session.send_api_request(
            'DELETE', '/user', data={'password': self.hash_password(password)})
        yield None

    def _get_key_url(self):
        return User.KEY_URL_FORMAT % self.name

    def _get_public_key_url(self):
        return User.PUBLIC_KEY_URL_FORMAT % self.name

    @reduce_coroutine()
    def get_public_key(self):
        """Get the user's public key string.

        Note: user.name must be set before using this method, either at the
        __init__() call or by using get_user_info().

        Returns:
            Promise<str>: the public key string.
        """
        response = yield self._session.download_storage_file(
            'GET', self._get_public_key_url())

        tmp_file = response.get('content', None)
        if not tmp_file:
            yield None
            return
        yield encryption.AsymmetricKey.load(tmp_file, main_context=True)

    @reduce_coroutine()
    def check_remote_key(self):
        """Download the user's GPG private key from the server, and add it to
        the keyring.

        Returns:
            Promise<boolean>: True if the operation succeeded. False if there
                is no remote key.
        """
        try:
            response = yield self._session.download_storage_file(
                'GET', self._get_key_url())
        except HTTPNotFoundError:
            yield False  # Key doesn't exists
            return

        with response.get('content', None) as tmp_file:
            AsymmetricKey.load(tmp_file, main_context=True)
            yield True

    def _upload_private_key(self, key_content):
        return self._session.send_storage_request(
            'PUT', self._get_key_url(), data=key_content)

    def _upload_public_key(self, key_content):
        return self._session.send_storage_request(
            'PUT', self._get_public_key_url(), data=key_content)

    def _remove_private_key(self):
        return self._session.send_storage_request(
            'DELETE', self._get_key_url())

    def _remove_public_key(self):
        return self._session.send_storage_request(
            'DELETE', self._get_public_key_url())

    @reduce_coroutine()
    def create_encryption_key(self, passphrase=''):
        """
        Create a new GPG key file and upload to server.

        Args:
            passphrase: the passphrase used to create the new GPG key.

        Returns:
            Promise<None>
        """
        key = yield encryption.create_key(self.name, passphrase)
        yield Promise.all([
            self._upload_private_key(key.export(secret=True)),
            self._upload_public_key(key.export())
        ])

    @reduce_coroutine()
    def _remove_encryption_key(self):
        """Remove the remote private & public key file.

        Returns:
            Promise<dict>
        """
        private_result, public_result = yield Promise.all([
            self._remove_private_key(),
            self._remove_public_key()
        ])
        yield {
            'private_key_result': private_result,
            'pub_key_result': public_result
        }

    def reset_encryption_key(self, passphrase=''):
        """
        Remove the current GPG key file & create a new one,
        then upload to server.

        Args:
            passphrase (optional): the passphrase used to create the new GPG
                key.

        Returns:
            Promise<None>
        """
        # TODO: remove local key file
        self.create_encryption_key(passphrase)


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from .session import Session

    # Load session & change password
    session = Session.from_user_credentials('test+test_api@bajoo.fr',
                                            'test+test_api@bajoo.fr').result()
    user = User.load(session).result()
    _logger.debug(user.change_password('test+test_api@bajoo.fr',
                                       'test+test_api_1@bajoo.fr')
                  .result())

    # Reset the old password
    session = Session.from_user_credentials('test+test_api@bajoo.fr',
                                            'test+test_api_1@bajoo.fr') \
        .result()
    user = User.load(session).result()
    _logger.debug(user.change_password('test+test_api_1@bajoo.fr',
                                       'test+test_api@bajoo.fr').result())

    # Load session and get user's information
    user_future = Session \
        .from_user_credentials('test+test_api_5@bajoo.fr',
                               'test+test_api_5@bajoo.fr') \
        .then(User.load)
    user = user_future.result()
    _logger.debug("User info = %s", user.get_user_info().result())
    _logger.debug(user.create_encryption_key().result())
    _logger.debug(user.get_public_key().result())
    _logger.debug(user._remove_encryption_key().result())
