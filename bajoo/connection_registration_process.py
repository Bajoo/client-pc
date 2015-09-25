# -*- coding: utf-8 -*-

import errno
import locale
import logging
import os
import sys

from . import stored_credentials
from .api import register, User
from .api.session import Session
from .common import config
from .common.i18n import N_, _
from .common.future import Future, resolve_dec, wait_all
from .network.errors import HTTPError

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
        Future<session, user>: A connected, valid session, and the user
            associated.
    """

    p = _ConnectionProcess(ui_factory)
    return p.run()


class _ConnectionProcess(object):

    def __init__(self, ui_factory):
        self.ui_factory = ui_factory
        self.ui_handler = None

        self.is_new_account = False

        self.user = None

        # Last used credentials, modified by log_user()
        self._username = None
        self._password = None
        self._refresh_token = None

        self._need_root_folder_config = False
        self._need_gpg_config = False

        self._root_folder_error = None
        self._gpg_error = None

    def _get_ui_handler(self):
        """Create the UI handler if it's not done yet, and returns it.

        Returns:
            UIHandlerOfConnection
        """
        if not self.ui_handler:
            _logger.debug('Load UI Handler')
            self.ui_handler = Future.resolve(self.ui_factory()).result()
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
            f = self.ask_user_credentials(username)

        f = f.then(self.save_credentials)
        f = f.then(self.load_user_info)

        # Phase 2: configuration
        f = f.then(self.check_user_configuration)

        # Phase 3: prevent the user and returns the token.
        return f.then(self.inform_user)

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

    def ask_user_credentials(self, username, errors=None):
        """Ask the user if he want to connect or to register an account."""
        ui_handler = self._get_ui_handler()

        f = ui_handler.get_register_or_connection_credentials(
            last_username=username, errors=errors)
        return f.then(self._use_credentials)

    def _use_credentials(self, credentials):
        """Callback called on submission of the register or connection form.

        It will use the given credentials to login, or to register the user.

        Returns:
            Future<Session>: the user session.
        """
        action, username, password = credentials

        _logger.debug('User has given username "%s" to performs action: %s'
                      % (username, action))

        def _on_register(_):
            self.is_new_account = True
            return self.log_user(username, password=password)

        if action is 'register':
            f = register(username, password)
            return f.then(_on_register, self._on_login_error)
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

        if isinstance(error, HTTPError):

            if error.err_code == 'account_not_activated':
                _logger.debug('login failed: the account is not activated.')
                log_user = lambda __: self.log_user(
                    self._username, password=self._password,
                    refresh_token=self._refresh_token)
                f = ui_handler.wait_activation()
                return f.then(log_user)

            _logger.debug('login failed due to error: %s (%s)' %
                          (error.err_code, error.code))

            if error.code == 401:
                message = N_('Invalid username or password.')
            elif error.code == 409:
                message = N_('There is already an account with this email.')
            else:
                message = error.message

            # Note: error.err_description is more accurate, but actually not
            # translated, and not always comprehensible for the end-user.
            return self.ask_user_credentials(self._username,
                                             errors=message)
        else:  # network error
            _logger.debug('login failed due to error: %s' % error)
            message = getattr(error, 'message',
                              N_('An error happened: %s') % error)
            return self.ask_user_credentials(self._username,
                                             errors=message)

            # TODO: detect network errors (like no internet)
            # and retry after a delay.

    def save_credentials(self, session):
        """Save the refresh token obtained, and clears the password.

        Returns:
            Session: the session received in argument.
        """
        stored_credentials.save(self._username, session.get_refresh_token())
        self._clear_credentials()
        return session

    def load_user_info(self, session):
        """Load ths user info of the session's user.

        When done, the self.user atgtribute will be a fully-loaded user.

        Returns:
            Future<Session>
        """

        def _fetch_user_info(user):
            self.user = user
            return user.get_user_info()

        f = User.load(session).then(_fetch_user_info)
        return f.then(lambda _: session)

    def check_user_configuration(self, session):
        """
        This is the begin of the phase 2: ensure proper configuration.
        At this point, we have a valid session.
        """
        _logger.info('Connection process phase 2: Configuration')

        self._session = session

        if self.is_new_account:
            self._need_gpg_config = True
            self._need_root_folder_config = True
            f = self._get_settings_and_apply()
        else:
            f = wait_all([
                self.check_bajoo_root_folder().then(self._set_folder_flag,
                                                    self._set_folder_flag),
                self.check_gpg_config().then(self._set_gpg_flag,
                                             self._set_gpg_flag)
            ])
            f = f.then(self._ask_config_if_flags)

        return f.then(lambda __: session)

    def _get_settings_and_apply(self):
        """Ask settings from the user, then apply them."""
        ui_handler = self._get_ui_handler()
        f = ui_handler.ask_for_settings(
            self._need_root_folder_config, self._need_gpg_config,
            root_folder_error=self._root_folder_error,
            gpg_error=self._gpg_error)
        return f.then(self._apply_setup_settings)

    def _ask_config_if_flags(self, __):
        if self._need_gpg_config or self._need_root_folder_config:
            return self._get_settings_and_apply()
        else:
            return None

    def _apply_setup_settings(self, settings):
        """Receive settings from the UI, and apply them.

        If the settings are invalid, the ui will be called agin,until the two
        checks pass.

        Returns:
            Future<None>: resolve when the settings have been applied.
        """
        root_folder_path, gpg_passphrase = settings
        futures = []

        if self._need_root_folder_config:
            f1 = self.set_root_folder(root_folder_path)
            f1 = f1.then(self.check_bajoo_root_folder)
            f1 = f1.then(self._set_folder_flag, self._set_folder_flag)
            futures.append(f1)
        if self._need_gpg_config:
            f2 = self.create_gpg_key(gpg_passphrase)
            f2 = f2.then(self.check_gpg_config)
            f2 = f2.then(self._set_gpg_flag, self._set_gpg_flag)
            futures.append(f2)

        return wait_all(futures).then(self._ask_config_if_flags)

    def _set_folder_flag(self, result):
        log_msg = str(result)
        if sys.version_info[0] < 3:  # Python 2
            log_msg = log_msg.decode('utf-8')
        if isinstance(result, Exception):
            if isinstance(result, (IOError, OSError)):
                msg = os.strerror(result.errno)
                if sys.version_info[0] < 3:  # Python 2
                    msg = str(msg).decode('utf-8')
                self._root_folder_error = N_('Error: %s' % msg)
            else:
                self._root_folder_error = N_(
                    'Error when applying the Bajoo root folder config:\n %s' %
                    log_msg)
            _logger.warning(
                'Error when applying the Bajoo root folder config: %s' %
                log_msg)

        self._need_root_folder_config = (result is not True)

    def _set_gpg_flag(self, result):

        if result is False:
            self._gpg_error = N_("You haven't yet registered a GPG key.")

        if isinstance(result, Exception):
            if isinstance(result, (IOError, OSError)):
                encoding = locale.getpreferredencoding()
                if sys.version_info[0] < 3:  # Python 2
                    result = unicode(str(result), encoding)
            self._gpg_error = N_('Error during the GPG key check:\n %s' %
                                 result)
            _logger.warning('Error when applying the GPG config: %s' % result)

        self._need_gpg_config = (result is not True)

    def check_bajoo_root_folder(self, __=None):
        """Check that the root Bajoo folder is valid.

        To be valid the bajoo folder should be defined in the user
        configuration (ie: already explicitly chosen), and the corresponding
        folder must exists.

        Returns:
            Future<boolean>: True if valid; Otherwise False.
        """
        root_folder = config.get('root_folder', unicode=True)

        if not root_folder:
            self._root_folder_error = None
            return Future.resolve(False)

        if not os.path.isdir(root_folder):
            self._root_folder_error = N_(
                "%s doesn't exists, or is not a directory" % root_folder)
            return Future.resolve(False)

        if not os.access(root_folder, os.R_OK | os.W_OK):
            self._root_folder_error = N_(
                "%s has not the read and/or write permissions." % root_folder)
            return Future.resolve(False)

        return Future.resolve(True)

    def check_gpg_config(self, __=None):
        """Check that the GPG config is valid and the user has a valid set of
        keys.

        First, it loads the GPG information known by the server. If there is
        none, the config is not valid.
        If there is a key, it's compared to the local key, or downloaded if
        there is not local key.

        Returns:
            Future<boolean>: True if the GPG config is valid; Otherwise None.
        """
        return self.user.check_remote_key()

    def create_gpg_key(self, passphrase):
        """Create a new GPG key and upload it.

        Returns:
            Future<None>: resolve when the user has a valid GPG key,
                synchronized with the server.
        """
        return self.user.create_encryption_key(passphrase)

    @resolve_dec
    def set_root_folder(self, root_folder_path):
        """Create the Bajoo root folder.

        Returns:
            Future<None>: resolve when the user has a valid bajoo root folder,
        """
        try:
            os.makedirs(root_folder_path)
            os.makedirs(os.path.join(root_folder_path, _('Shares')))
            _logger.debug('Create Bajoo root folder "%s"' % root_folder_path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(root_folder_path):
                pass  # Folder already exists.
            else:
                _logger.warning('Unable to create Bajoo root folder "%s".'
                                ' See the error below.'
                                % root_folder_path, exc_info=True)
                raise

        config.set('root_folder', root_folder_path)

    def inform_user(self, session):
        """Informs the user interface if it's been used.

        At this point, the user is successfully logged. The UI should act in
        consequence.
        """
        if self.ui_handler:
            self.ui_handler.inform_user_is_connected()

        return session, self.user
