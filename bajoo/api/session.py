# -*- coding: utf-8 -*-

IDENTITY_API_URL = 'https://127.0.0.1:3000'
STORAGE_API_URL = 'https://192.168.2.100:8080'

CLIENT_ID = 'e2676e5d1fff42f7b32308e5eca3c36a'
CLIENT_SECRET = '<client-secret>'


class BajooOAuth2Session(object):
    def __init__(self):
        self.access_token = None

    def fetch_token(self, token_url, email, password):
        """
        Fetch a new access_token using email & password.

        Args:
            token_url:
            email:
            password:

        Returns:
            Future<None>
        """
        pass

    def refresh_token(self, refresh_token):
        """
        Fetch a new access_token using the refresh_token.

        Args:
            refresh_token:

        Returns:
            Future<None>
        """
        pass


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
        pass

    @staticmethod
    def load_session(refresh_token):
        """
        Restore an old session using refresh_token.

        Returns:
            Future<Session>
        """
        pass

    def get_refresh_token(self):
        """
        Get the refresh_token.

        Returns:
            (str) The refresh token
        """
        pass

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