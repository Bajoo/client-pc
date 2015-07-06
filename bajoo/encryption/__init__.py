# -*- coding: utf-8 -*-

"""Provides functions to encrypt and decrypt files asynchronously.

The encryption module is an interface using the GPG executable.
It supports two main features:
- The encryption and decryption of arbitrary files.
- The creation and use of asymmetric GPG keys.

The initialisation of GPG, is done transparently for the caller.
A global keyring is instantiated (and kept between executions), for storing
keys regularly used.
It's also possible to use a GPG key which is not in the global keyring,
without importing it.

All the heavy operations are executed asynchronously, and use ``Future`` to
communicate the result.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
from multiprocessing import cpu_count
from gnupg import GPG

from ..common.future import then
from .asymmetric_key import AsymmetricKey

_logger = logging.getLogger(__name__)


_thread_pool = ThreadPoolExecutor(max_workers=cpu_count())

# main GPG() instance
_gpg = None


def _get_gpg_context():
    """Initialize the GPG main keyring."""
    global _gpg

    if not _gpg:
        # TODO: set real path for test_keyring !!!
        _gpg = GPG(verbose=False, gnupghome='./test_keyring')
        # TODO: manages exceptions
    return _gpg


def create_key(email, passphrase):
    """Generate a new GPG key.

    Returns:
        Future<AsymmetricKey>
    """
    _logger.debug('Start to generate a new GPG key ...')
    gpg = _get_gpg_context()

    input_data = gpg.gen_key_input(key_length=2048, name_email=email,
                                   name_comment='Bajoo user key',
                                   passphrase=passphrase)
    f = _thread_pool.submit(gpg.gen_key, input_data)

    def on_key_generated(data):
        _logger.info('New GPG key created: %s', data.fingerprint)
        if not data:
            pass  # TODO: raise Exception
        return AsymmetricKey(gpg, data.fingerprint)

    return then(f, on_key_generated)


def encrypt(source, recipients):
    """Asynchronously encrypt a file for a list of recipients.

    The encryption operation are done using GPG, in another thread.

    The source file is not modified. The result is stored in a temporary file,
    which will be deleted as soon as it will be closed. It's up to the caller
    to close it when the file is no more necessary.

    Args:
        source (str|file): The source file to encrypt. If it's a str, it must
            be a valid file path. If it's a file-like object, it's expected to
            have its pointer to the beginning of the file.
        recipients (list of AsymmetricKey): the list of keys who will be able
            to read the resulting encrypted file.
    Returns:
        Future<TemporaryFile>: A Future returning a temporary file of the
            resulting encrypted data.
    """
    raise NotImplemented()


def decrypt(source, key=None):
    """Asynchronously decrypt a file.

    Decrypt a file using the GPG executable.

    By default, the required key is searched from the general Bajoo keyring.
    It's possible to indicate which key to use, by passing an arbitrary key in
    argument. If so, the selected key will be used without be added to the
    keyring.

    The result is stored in a temporary file, which will be deleted as soon as
    it will be closed. It's up to the caller to close it when the file is no
    more necessary.

    Args:
        source (str|file): The source file to encrypt. If it's a str, it must
            be a valid file path. If it's a file-like object, it's expected to
            have its pointer to the beginning of the file.
        key (AsymmetricKey, optional): If set, use this key for the decryption,
            instead of using the global Bajoo keyring.
    Returns:
        Future<TemporaryFile>: A Future returning a temporary file of the
            resulting decrypted data.
    """
    raise NotImplemented()


def import_key(key):
    """Add a key to the global Bajoo keyring.

    The key will be saved on the disk, and will be available for any GPG
    operation. It will persists between executions of the program.

    Args:
        key (AsymmetricKey): key to add to the global Bajoo keyring.
    """
    raise NotImplemented()


def get_key(key_id):
    """Find a key by id, from the global Bajoo keyring.

    Args:
        key_id (str): ID of the key. It can be the short ID, or the
            fingerprint (better).
    Returns:
        AsymmetricKey: the searched key. None the key is not found.
    """
    raise NotImplemented()


def get_key_by_email(email):
    """Find a key by email, from the global Bajoo keyring.

    If many keys has been associated to this email, only the first will be
    returned.

    Args:
        email (str): email associated to the key.
    Returns:
        AsymmetricKey: the searched key. None the key is not found.
    """
    raise NotImplemented()
