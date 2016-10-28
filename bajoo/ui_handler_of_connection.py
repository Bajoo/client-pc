# -*- coding: utf-8 -*-

import abc


class UserQuit(Exception):
    """Exception raised when the user quit Bajoo during an input operation."""
    pass


class UIHandlerOfConnection(object):
    """Abstract class representing user interactions before the connexion.

    It's the interface between the connect_or_register process and the user.

    It will be used to ask the user all information needed by the connection
    process, using these asynchronous methods. The result will be wrapped in
    Future instances.
    If an unexpected event occurs (exceptions, but also user events like
    window closing), the methods should raise an exception.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_register_or_connection_credentials(self, last_username=None,
                                               errors=None):
        """Ask user for credentials to connect or register him.

        Args:
            last_username (str, optional): last used username, if any.
            errors (str, optional): If set, error message of the previous
                tentative.
        Returns:
            Future<(str, str, str)>: the first return value is either
                'registration' or 'connection'. the second value contains the
                user name (or email). The third value is the password.

        Raises:
            UserQuit: the user quit the application. The caller should
                terminate.
        """
        pass

    @abc.abstractmethod
    def wait_activation(self, username):
        """Ask the user to activate his account, and wait his confirmation.

        The future resolves when it's done.

        Note that the future resolve when the user *tells* his account is
        validated, but this may be not the case.

        Args:
            username (Text): email address of the user we wait the activation.
        Returns:
            Future<None>: resolves when the user indicates he has validated
                his account.

        Raises:
            UserQuit: the user quit the application. The caller should
                terminate.
        """
        pass

    @abc.abstractmethod
    def ask_for_settings(self, folder_setting=True, key_setting=True,
                         root_folder_error=None, gpg_error=None):
        """Ask to user to precise some important settings.

        The caller may ask for two settings independently: the Bajoo root
        folder path, or the passphrase for generating a new GPG user key, or
        both. The caller specifies which setting he wants, using arguments.

        Notes:
            At least one of ``folder_setting``, ``key_setting`` or
            ``gpg_error`` must be True.
            If `key_setting` is False, but `gpg_error`is True, the passphrase
            exists (and shouldn't be changed) but is unavailable.

        Args:
            folder_setting (boolean): If True, this method asks the Bajoo root
                folder path.
            key_setting (boolean): If True, this method asks for the passphrase
                of the GPG user key.
            root_folder_error (str, optional):  if set, error message of the
                previous tentative to set the bajoo root folder.
            gpg_error (str, optional): if set, error message or the previous
                tentative to set the GPG config.
        returns:
            Future<str, str>: the first return value contains the folder path,
                and the second contains the passphrase for the GPG user key.
                If only one element is asked, the other can be None. If the
                user don't want any passphrase, it should be None.

        Raises:
            UserQuit: the user quit the application. The caller should
                terminate.
        """
        pass

    @abc.abstractmethod
    def inform_user_is_connected(self):
        """Indicate that the user has been connected.

        This method is called by the ``connect_and_register`` process when the
        connection is effective. The UI handler should inform the user, and
        close itself after that.

        No other method will be called after this one; The process is over.
        """
        pass
