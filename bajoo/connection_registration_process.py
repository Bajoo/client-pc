# -*- coding: utf-8 -*-

import errno
import locale
import logging
import os
import sys

from .api import User
from .api.session import Session
from .common import config
from .common.i18n import N_, _
from .encryption import set_gpg_home_dir
from .network.errors import HTTPError
from . import promise
from .user_profile import UserProfile


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

        self.profile = None
        self.user = None

        self._username = None

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
            self.ui_handler = self.ui_factory().result()
        return self.ui_handler

    @promise.reduce_coroutine(safeguard=True)
    def run(self):
        """Entry point of the connection process.

        Returns only when the player is connected, or if there is a fatal
        error.

        Returns:
            Future<session>: A connected, valid session.
        """
        self.profile = UserProfile.get_last_profile()

        username = refresh_token = None
        if self.profile:
            username = self.profile.email
            refresh_token = self.profile.refresh_token

        _logger.debug('Connection process phase 1: LogIn')

        # Phase 1: connection
        session = yield self.connection(username, refresh_token=refresh_token)

        self.save_credentials(session)
        yield self.load_user_info(session)

        # Phase 2: configuration
        yield self.check_user_configuration(session)

        # Phase 3: prevent the user and returns the token.
        self.inform_user()

        yield session, self.user, self.profile

    @promise.reduce_coroutine(safeguard=True)
    def connection(self, username, password=None, refresh_token=None,
                   error_msg=None):
        """Connect the user from the credentials given.

        Either refresh_token or password must be set.
        If the connection fails, the function will the user for other
        credentials, and try again.
        If the user account is not activated, It will informs the user, and try
        again.

        Note: error_msg is ignored if refresh_token is set, as we don't
        communicate with the user.

        Args:
            username (str): user email.
            password (str, optional): user password
            refresh_token (str, optional): valid refresh_token
            error_msg (str, optional): if set, message of a previous error that
                will be displayed to the user.
        Returns:
            Promise<Session>
        """
        self._username = username

        if refresh_token:  # Login automatic
            _logger.debug('Log user "%s" using refresh token ...' % username)
            try:
                yield Session.from_refresh_token(refresh_token)
            except Exception as error:
                yield self._connection_error_handler(
                    error, username, refresh_token=refresh_token)

        else:
            if not password:
                ui_handler = self._get_ui_handler()
                credentials = yield \
                    ui_handler.get_register_or_connection_credentials(
                        last_username=username, errors=error_msg)
                action, username, password = credentials
                self._username = username

                _logger.debug('User has given username "%s" to performs action'
                              ': %s' % (username, action))
            else:
                action = 'login'

            try:
                if action == 'register':
                    lang = config.get('lang')
                    yield User.create(username, password, lang)
                    self.is_new_account = True

                _logger.debug('Log user "%s" using password ...' % username)
                yield Session.from_user_credentials(username, password)
            except Exception as error:
                yield self._connection_error_handler(error, username,
                                                     password=password)

    @promise.reduce_coroutine(safeguard=True)
    def _connection_error_handler(self, error, username, password=None,
                                  refresh_token=None):
        """Error handler of the `self.connection` method.

        This handler catch error related to the connection or the registering.
        These are usually network error or API errors.

        Depending of the error, we should informs the user, or retry latter.
        In any case, the returned Promise will resolve only when the user will
        be connected.

        In any case, the `self.connection` method is called again, with an
        error message if needed.

        Args:
            error (Exception)
            username (str): user email.
            password (str, optional): user password
            refresh_token (str, optional): valid refresh_token
        Returns:
            Future<Session>: the user session.
        """

        if isinstance(error, HTTPError):

            if error.err_code == 'account_not_activated':
                _logger.debug('login failed: the account is not activated.')
                ui_handler = self._get_ui_handler()
                yield ui_handler.wait_activation()
                yield self.connection(username, password=password,
                                      refresh_token=refresh_token)
                return

            _logger.debug('login failed due to error: %s (%s)' %
                          (error.err_code, error.code))

            if error.code == 401:
                if error.err_code == 'invalid_client':
                    message = N_('This program\'s version is no longer'
                                 ' supported by Bajoo service. '
                                 'Please update to continue.\n')
                else:
                    message = N_('Invalid username or password.')
            elif error.code == 409:
                message = N_('There is already an account with this email.')
            else:
                message = error.message

            # Note: error.err_description is more accurate, but actually not
            # translated, and not always comprehensible for the end-user.
            yield self.connection(username, error_msg=message)
        else:  # network error
            _logger.debug('login failed due to error: %s' % error)
            message = getattr(error, 'message',
                              N_('An error occurred: %s') % error)

            yield self.connection(username, error_msg=message)

            # TODO: detect network errors (like no internet)
            # and retry after a delay.

    def save_credentials(self, session):
        """Save the refresh token obtained, and clears the password.

        Returns:
            Session: the session received in argument.
        """
        if not self.profile or self.profile.email != self._username:
            self.profile = UserProfile(self._username)
        self.profile.refresh_token = session.refresh_token

        return session

    @promise.reduce_coroutine(safeguard=True)
    def load_user_info(self, session):
        """Load the user info of the session's user.

        When done, the self.user attribute will be a fully-loaded user.

        Returns:
            Future<Session>
        """
        user = yield User.load(session)
        self.user = user
        yield user.get_user_info()

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
            f = promise.Promise.all([
                self.check_bajoo_root_folder().then(self._set_folder_flag,
                                                    self._set_folder_flag),
                self.check_gpg_config().then(self._set_gpg_flag,
                                             self._set_gpg_flag)
            ])
            f = f.then(self._ask_config_if_flags)

        return f

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
        root_folder_path, gpg_passphrase, save_passphrase = settings
        futures = []

        if save_passphrase:
            self.profile.passphrase = gpg_passphrase
        else:
            self.profile.passphrase = None

        if self._need_root_folder_config:
            f1 = self.set_root_folder(root_folder_path)
            f1 = f1.then(self.check_bajoo_root_folder)
            f1 = f1.then(self._set_folder_flag, self._set_folder_flag)
            futures.append(f1)
        if self._need_gpg_config:
            set_gpg_home_dir(self.profile.gpg_folder_path)
            f2 = self.user.create_encryption_key(gpg_passphrase)
            f2 = f2.then(self.check_gpg_config)
            f2 = f2.then(self._set_gpg_flag, self._set_gpg_flag)
            futures.append(f2)

        return promise.Promise.all(futures).then(self._ask_config_if_flags)

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
            self._gpg_error = \
                N_('Error during the GPG key check:\n %s') \
                % result
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
        root_folder = self.profile.root_folder_path

        if not root_folder:
            self._root_folder_error = None
            return promise.Promise.resolve(False)

        if not os.path.isdir(root_folder):
            self._root_folder_error = N_(
                "%s doesn't exist, or is not a directory" % root_folder)
            return promise.Promise.resolve(False)

        if not os.access(root_folder, os.R_OK | os.W_OK):
            self._root_folder_error = N_(
                "%s has not the read and/or write permissions." % root_folder)
            return promise.Promise.resolve(False)

        return promise.Promise.resolve(True)

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
        set_gpg_home_dir(self.profile.gpg_folder_path)
        return self.user.check_remote_key()

    @promise.wrap_promise
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

        self.profile.root_folder_path = root_folder_path

    def inform_user(self):
        """Informs the user interface if it's been used.

        At this point, the user is successfully logged. The UI should act in
        consequence.
        """
        if self.ui_handler:
            self.ui_handler.inform_user_is_connected()
