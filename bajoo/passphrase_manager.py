#  -*- coding:utf-8 -*-

import logging
from threading import Lock

_logger = logging.getLogger(__name__)


class PassphraseManager(object):
    """Keep passphrase(s) in memory and transmit them to the encryption module.

    If the user doesn't want to gives his passphrase, the `_rejected` flags is
    set to True, and any subsequenty call are ignored. This state is
    reinitialized with a call to `set_passphrase()`.
    """

    def __init__(self, user_profile):
        """
        Args:
            user_profile (UserProfile): profile used to persistently stores
                the passphrase.
        """
        self._user_input_callback = None
        self._passphrase = None
        self._rejected = False
        self._lock = Lock()

        self._user_profile = user_profile

    def set_user_input_callback(self, callback):
        """Set the callback used to ask the user his passphrase.

        Args:
            callback (callable): function who takes a boolean argument
                'is_retry', and must return a tuple containing the passprhase,
                and a boolean telling if should memorize the passphrase.
        """
        self._user_input_callback = callback

    def get_passphrase(self, is_retry):
        """Retrieve the passphrase either from cache or by asking the user

        If there is already a passphrase value in memory, it's returned.
        If not, the function search the passphrase on the disk (if the user has
        chosen the "remember" option).
        If we still haven't the passphrase, we ask the user using the callback
        specified by a previous call to `set_user_input_callback`.

        This method is thread-safe

        Args:
            email (str): email of the user.
            is_retry (boolean): if True, it's not the first time
        Returns:
            text: the passphrase. None if the user has refused to provide the
                passphrase
        """
        _logger.log(5, 'Get passphrase (retry=%s, rejected=%s)',
                    is_retry, self._rejected)
        with self._lock:
            if self._rejected:
                return None

            if not is_retry:
                if self._passphrase:
                    return self._passphrase
                self._passphrase = self._user_profile.passphrase
                if self._passphrase:
                    return self._passphrase

            if self._user_input_callback:
                _logger.debug('Ask passphrase to the user.')
                passphrase, remember_it = self._user_input_callback(is_retry)
                self._passphrase = passphrase
                self._rejected = passphrase is None
                if remember_it:
                    self._user_profile.passphrase = passphrase
                return passphrase
            return None

    def set_passphrase(self, passphrase, remember_on_disk=False):
        """Set the passphrase.

        It also reinitialize the "rejected" status.

        Args:
            email (str): user email (Bajoo account)
            passphrase (str): passphrase. If None, the previous passphrase will
                be forgotten.
            remember_on_disk (boolean): If True the passphrase will be saved
                on disk, and retrieved at next use of bajoo.
        """
        if passphrase:
            _logger.debug('Set passphrase.')
        else:
            _logger.debug('Forget passphrase.')
        self._passphrase = passphrase
        self._rejected = False
        if remember_on_disk:
            self._user_profile.passphrase = passphrase

    def remove_passphrase(self):
        """Forgot the passphrase an erase it from disk.

        It also reinitialize the "rejected" status.
        """
        _logger.debug('Remove & Forget passphrase.')
        self._passphrase = None
        self._rejected = False
        self._user_profile.passphrase = None
