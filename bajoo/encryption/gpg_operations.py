# -*- coding: utf-8 -*-
"""GPG operations

Theses functions should be called in the process dedicated to GPG, as they are
all blocking.
"""

import atexit
import logging
import os
import tempfile
from ..common.path import get_cache_dir
from .errors import DecryptError, EncryptError, PassphraseError

_logger = logging.getLogger(__name__)

_tmp_dir = None


def _get_tmp_dir():
    """get a temporary directory. The directory is created at fist call."""
    global _tmp_dir

    if not _tmp_dir:
        try:
            _tmp_dir = tempfile.mkdtemp(dir=get_cache_dir())
        except:
            _logger.exception('Error when creating tmp dir for encryption '
                              'files')
            raise
    return _tmp_dir


@atexit.register
def _clean_tmp():
    global _tmp_dir

    if not _tmp_dir:
        return
    try:
        os.removedirs(_tmp_dir)
        _tmp_dir = None
    except:
        pass


def encrypt(gpg, source, recipients):
    """Encrypt a file.

    Args:
        gpg (gnupg.GPG): GPG context
        source (File): File-like object that will be encrypted
        recipients (list): the list of keys who will be able
            to read the resulting encrypted file.
    Returns:
        str: path of the resulting file.
    Raises:
        KeyGenError
    """

    # Create empty file used as GPG output
    tmp_dir = _get_tmp_dir()
    with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir) as tf:
        dst_path = tf.name

    list_fingerprint = [key.fingerprint for key in recipients]
    result = gpg.encrypt_file(source, list_fingerprint, output=dst_path,
                              armor=False, always_trust=True)

    if not result:
        raise EncryptError('Encryption failed', result)
    return dst_path


def decrypt(gpg, source, passphrase=None):
    """

    Args:
        gpg (gnupg.GPG): GPG context
        source (File): File-like object that will be decrypted
        passphrase (str, optional): passphrase needed to decrypt the file.
    Returns:
        str: path of the resulting file.
    Raises:
        PassphraseError: Either the passphrase is invalid, or it is required
            but not set.
        DecryptError:
    """
    tmp_dir = _get_tmp_dir()
    with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir) as tf:
        dst_path = tf.name

    result = gpg.decrypt_file(source, output=dst_path, passphrase=passphrase)

    if not result:
        # pkdecrypt codes are defined in libgpg-error (in err-codes.h)
        if '[GNUPG:] ERROR pkdecrypt_failed 11' in result.stderr:
            raise PassphraseError('Decryption failed: probably a bad '
                                  'passphrase', result)
        if '[GNUPG:] MISSING_PASSPHRASE' in result.stderr:
            raise PassphraseError('Decryption failed: missing passphrase',
                                  result)
        raise DecryptError('Decryption failed: %s' % result.status, result)

    return dst_path


def gen_key(gpg, **kwargs):
    input_data = gpg.gen_key_input(**kwargs)
    return gpg.gen_key(input_data)
