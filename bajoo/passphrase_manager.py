#  -*- coding:utf-8 -*-

import errno
import logging
import os.path
from .common.path import get_data_dir
from .common.util import xor

_logger = logging.getLogger(__name__)


class PassphraseManager(object):
    """Store the passphrase(s) and transmit them to the encryption module.

    If the user doesn't want to gives his passphrase, the `_rejected` flags is
    set to True, and any subsequenty call are ignored. This state is
    reinitialized with a call to `set_passphrase()`.
    """

    def __init__(self):
        self._user_input_callback = None
        self._passphrase = None
        self._rejected = False

    def set_user_input_callback(self, callback):
        """Set the callback used to ask the user his passphrase.

        Args:
            callback (callable): function who takes a boolean argument
                'is_retry', and must return a tuple containing the passprhase,
                and a boolean telling if should memorize the passphrase.
        """
        self._user_input_callback = callback

    def get_passphrase(self, email, is_retry):
        """Retrieve the passphrase either from cache or by asking the user

        If there is already a passphrase value in memory, it's returned.
        If not, the function search the passphrase on the disk (if the user has
        chosen the "remember" option).
        If we still havn't the passphrase, we ask the user usoing the callback
        specified by a previous call to `set_user_input_callback`.

        Args:
            email (str): email of the user.
            is_retry (boolean): if True, it's not the first time
        Returns:
            text: the passphrase. None if the user has refused to provide the
                passphrase
        """
        if self._rejected:
            return None

        if not is_retry:
            if self._passphrase:
                return self._passphrase
            self._passphrase = self._load_passphrase_from_disk(email)
            if self._passphrase:
                return self._passphrase

        if self._user_input_callback:
            passphrase, remember_it = self._user_input_callback(is_retry)
            self._passphrase = passphrase
            self._rejected = passphrase is None
            if remember_it:
                self._save_passphrase_on_disk(passphrase, email)
            return passphrase
        return None

    def set_passphrase(self, email, passphrase, remember_on_disk=False):
        """Set the passphrase.

        It also reinitialize the "rejected" status.

        Args:
            email (str): user email (Bajoo account)
            passphrase (str): passphrase. If None, the previous passphrase will
                be forgotten.
            remember_on_disk (boolean): If True the passphrase will be saved
                on disk, and retrieved at next use of bajoo.
        """
        self._passphrase = passphrase
        self._rejected = False
        if remember_on_disk:
            self._save_passphrase_on_disk(passphrase, email)

    @staticmethod
    def _save_passphrase_on_disk(passphrase, key):
        """Write the passphrase on the disk.

        Args:
            passphrase (bytes/text): passphrase to save. If None, the
                previously saved passphrase is deleted.
            key (bytes/text): key used to performs basic encryption.
        """
        passphrase_path = os.path.join(get_data_dir(), 'passphrase')

        if passphrase is None:
            try:
                os.remove(passphrase_path)
            except (OSError, IOError) as e:
                if e.errno != errno.ENOENT:
                    _logger.warning('Remove the passphrase file has failed.',
                                    exc_info=True)
            return

        enc_passphrase = xor(passphrase, key)
        try:
            with open(passphrase_path, 'wb') as f:
                f.write(enc_passphrase)
        except (IOError, OSError):
            _logger.warning('Unable to store passphrase on the disk.',
                            exc_info=True)

    @staticmethod
    def _load_passphrase_from_disk(key):
        """Load and returns the passprhase stored on the disk.

        Args:
            key (bytes/text): key used to decrypt the file.
        Returns:
            passphrase (text); None if there is none.
        """
        passphrase_path = os.path.join(get_data_dir(), 'passphrase')

        try:
            with open(passphrase_path, 'rb') as f:
                enc_passphrase = f.read()
                return xor(enc_passphrase, key).decode('utf-8')
        except (IOError, OSError) as e:
            if e.errno != errno.ENOENT:
                _logger.warning('Unable to read passphrase from the disk',
                                exc_info=True)
        return None
