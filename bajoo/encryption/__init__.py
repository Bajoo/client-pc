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

import logging


_logger = logging.getLogger(__name__)


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
        recipients (list of AsyncKey): the list of keys who will be able to
            read the resulting encrypted file.
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
        key (AsyncKey, optional): If set, use this key for the decryption,
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
        key (AsyncKey): key to add to the global Bajoo keyring.
    """
    raise NotImplemented()


def get_key(key_id):
    """Find a key by id, from the global Bajoo keyring.

    Args:
        key_id (str): ID of the key. It can be the short ID, or the
            fingerprint (better).
    Returns:
        AsyncKey: the searched key. None the key is not found.
    """
    raise NotImplemented()


def get_key_by_email(email):
    """Find a key by email, from the global Bajoo keyring.

    If many keys has been associated to this email, only the first will be
    returned.

    Args:
        email (str): email associated to the key.
    Returns:
        AsyncKey: the searched key. None the key is not found.
    """
    raise NotImplemented()
