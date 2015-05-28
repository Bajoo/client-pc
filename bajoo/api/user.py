# -*- coding: utf-8 -*-
import logging
from hashlib import sha256

from ..common.future import resolve_dec


_logger = logging.getLogger(__name__)


class User(object):
    def __init__(self, name="", session=None):
        self.name = name
        self._session = session

    @staticmethod
    @resolve_dec
    def load(session):
        """
        Create a user object from an existing session.

        Args:
            session (bajoo.api.Session): an authorized session

        Returns:
            Future<User>
        """
        if not session:
            raise ValueError("Empty or null session")

        # Refresh token if necessary
        if not session.is_authorized():
            return session.refresh_token().then(
                lambda __: User(session=session))
        else:
            # Valid session, so return user
            return User(session=session)

    @staticmethod
    def hash_password(password):
        """Convert a password to a hash usable by the Bajoo API"""
        return sha256(password.encode('utf-8')).hexdigest()

    def get_quota(self):
        """
        Returns Future<(int, int)>: used & total storage space.
        """
        raise NotImplemented

    def change_password(self, old_password, new_password):
        """
        Change current user password

        Arguments:
            old_password (str): current password in plain text
            new_password (str): new password in plain text

        Returns:
            Future<None>
        """
        hashed_old_password = self.hash_password(old_password)
        hashed_new_password = self.hash_password(new_password)
        data = {'password': hashed_old_password,
                'new_password': hashed_new_password}

        # TODO: analyze result & handle error
        return self._session.send_json_request(
            'PATCH', '/user', data=data)

    def delete_account(self, password):
        """
        Remove current account from Bajoo.

        Args:
            password (str): current password in plain text

        Returns:
            Future<None>
        """
        raise NotImplemented

    def get_public_key(self):
        """Get the user's public key string"""
        raise NotImplemented

    def create_encryption_key(self, passphrase):
        """
        Create a new GPG key file and upload to server.

        Args:
            passphrase: the passphrase used to create the new GPG key.

        Returns:
            Future<None>
        """
        raise NotImplemented

    def reset_encryption_key(self, passphrase):
        """
        Remove the current GPG key file & create a new one,
        then upload to server.

        Args:
            passphrase: the passphrase used to create the new GPG key.

        Returns:
            Future<None>
        """
        raise NotImplemented


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from .session import Session

    # Load session & change password
    session = Session.create_session('stran+test_api@bajoo.fr',
                                     'stran+test_api@bajoo.fr').result()
    user = User.load(session).result()
    _logger.debug(user.change_password('stran+test_api@bajoo.fr',
                                       'stran+test_api_1@bajoo.fr')
                  .result())

    # Reset the old password
    session = Session.create_session('stran+test_api@bajoo.fr',
                                     'stran+test_api_1@bajoo.fr').result()
    user = User.load(session).result()
    _logger.debug(user.change_password('stran+test_api_1@bajoo.fr',
                                       'stran+test_api@bajoo.fr')
                  .result())
