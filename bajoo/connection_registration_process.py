# -*- coding: utf-8 -*-

import logging
from functools import partial

from . import stored_credentials
from .api.session import Session
from .ui_handler_of_connection import UserInterrupt

_logger = logging.getLogger(__name__)


def connect_or_register(ui_factory):
    """Start the process of connection and/or registration.

    This process will follow all necessary steps to register (optionally) and
    connect the user, according to his will.
    If the process can be done with the already present informations, the
    operation will be transparent for the user.
    If not (ie: no credentials saved), the UI handler factory, received in
    parameter, will be called to create an UI handler. this UI handler will be
    used to communicate with the user.

    The default behavior is to connect using the saved credentials. If it
    doesn't work, the user is asked to give his credentials, or create a new
    account (registration). In case of registration, the user will be
    automatically connected after the account creation.

    The Future will resolve only when the user will be completely connected,
    with a valid session and a valid GPG key, present in local device.
    If the user never connects, by not responding to UI handler messages, then
    the returned future will never resolve.

    Args:
        ui_factory (callable<UIHandlerOfConnection>): callable who returns an
            UIHandlerOfConnection. This function will never be called more
            than one.
    Returns:
        Future<session>: A connected, valid session.
    """

    p = _ConnectionProcess(ui_factory)
    return p.run()


class _ConnectionProcess(object):

    def __init__(self, ui_factory):
        self.ui_factory = ui_factory
        self.ui_handler = None

        # Last used credentials, modified by log_user()
        self._username = None
        self._password = None
        self._refresh_token = None

    def _get_ui_handler(self):
        """Create the UI handler if it's not done yet, and returns it.

        Returns:
            UIHandlerOfConnection
        """
        if not self.ui_handler:
            _logger.debug('Load UI Handler')
            self.ui_handler = self.ui_factory()
        return self.ui_handler

    def _clear_credentials(self):
        self._username = None
        self._refresh_token = None
        self._password = None

    def run(self):
        """Entry point of the connection process.

        Returns only when the player is connected, or if there is a fatal
        error.

        Returns:
            Future<session>: A connected, valid session.
        """
        username, refresh_token = stored_credentials.load()

        _logger.debug('Connection process phase 1: LogIn')

        # Phase 1: connection
        if refresh_token:
            f = self.log_user(username, refresh_token=refresh_token)
        else:
            ui_handler = self._get_ui_handler()
            action = partial(ui_handler.get_register_or_connection_credentials,
                             last_username=username)
            on_error = partial(self._ui_error, action)
            f = action().then(self._use_credentials, on_error)

        f = f.then(self.save_credentials)

        # Phase 2: configuration
        return f.then(self.check_user_configuration)

    def log_user(self, username, refresh_token=None, password=None):
        """Connect the user from the credentials given.

        Either refresh_token or password must be set.
        If the connection fails, the function will the user for other
        credentials, and try again.
        If the user account is not activated, It will informs the user, and try
        again.

        Args:
            username (str): user email.
            refresh_token (str, optional): valid refresh_token
            password (str, optional): user password
        Returns:
            Future<Session>: the user session.
        """
        self._username = username
        self._password = password
        self._refresh_token = refresh_token

        if username and password:
            _logger.debug('Log user "%s" using password ...' % username)
            f = Session.create_session(username, password)
        else:
            _logger.debug('Log user "%s" using refresh token ...' % username)
            f = Session.load_session(refresh_token)
        return f.then(None, self._on_login_error)

    def _use_credentials(self, credentials):
        """Callback called on submission of the register or connection form.

        It will use the given credentials to login, or to register the user.

        Returns:
            Future<Session>: the user session.
        """
        action, username, password = credentials

        _logger.debug('User has given username "%s" to performs action: %s'
                      % (username, action))

        if action is 'register':
            # TODO: implements ...
            pass
        else:
            return self.log_user(username, password=password)

    def _on_login_error(self, error):
        """Callback called when the API has returned an error on connexion.

        Depending of the error, we should informs the user, or retry latter.
        In any case, the returned future will resolve only when the user will
        be connected.

        Returns:
            Future<Session>: the user session.
        """
        ui_handler = self._get_ui_handler()

        # TODO: really check error is NotActivatedAccount
        if error is 'NotActivatedAccount':
            log_user = partial(self.log_user, self._username,
                               password=self._password,
                               refresh_token=self._refresh_token)
            f = ui_handler.wait_activation()
            on_error = partial(self._ui_error, ui_handler.wait_activation)
            return f.then(log_user, on_error)
        else:
            # TODO: format errors
            error = 'ERROR'

            action = partial(ui_handler.get_register_or_connection_credentials,
                             last_username=self._username, errors=error)
            on_error = partial(self._ui_error, action)

            return action().then(self._use_credentials, on_error)

            # TODO: detect network errors (like no internet)
            # and retry after a delay.

    def _ui_error(self, ui_action, error):
        """Callback of UI handler errors.

        Note: the UserQuit is not caught: if it happens, it will go out of
        all the calls, and stop everything.

        Args:
            ui_action (callable): action to call when the user is ready.
        Returns:
            Future<?>: Future chained to the ``ui_action`` result.
        """
        if isinstance(error, UserInterrupt):
            _logger.debug('User interruption. Wait that the user resume ...')
            return self._get_ui_handler().wait_user_resume().then(ui_action)
        raise error

    def save_credentials(self, session):
        """Save the refresh token obtained, and clears the password.

        Returns:
            Session: the session received in argument.
        """
        stored_credentials.save(self._username, session.get_refresh_token())
        self._clear_credentials()
        return session

    def check_user_configuration(self):
        """
        This is the begin of the phase 2: ensureq proper configuration.
        At this point, we have a valid session.
        """
        _logger.info('Connection process phase 2: Configuration')
        # TODO
        pass
