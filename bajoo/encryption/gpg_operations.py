# -*- coding: utf-8 -*-
"""GPG operations

Theses functions should be called in the process dedicated to GPG, as they are
all blocking.
"""

import atexit
import logging
import os
import os.path
import shutil
import tempfile
import threading
import time
from ..common.path import get_cache_dir
from ..common.strings import err2unicode
from .errors import DecryptError, EncryptError, PassphraseError

_logger = logging.getLogger(__name__)

_tmp_dir = None


def _migration_remove_tmp_folders():
    """Delete all old tmp folders.

    A bug in previous versions of Bajoo was preventing the temporary folder
    deletion. As result, some users have accumulate a huge amount of empty
    folders. This method removes all folders in the cache directory.

    As the operation may be slow (and IO-expensive), a dedicated thread will
    do the job for the "migration".
    """
    try:
        tmp_dirs = os.listdir(get_cache_dir())
    except (IOError, OSError) as err:
        _logger.info('unable to remove old temporary folders: %s',
                     err2unicode(err))
        return

    def _remove_tmp_dir_thread(tmp_dirs):
        _logger.debug('Start cleaning old tmp dirs.')
        cache_dir = get_cache_dir()
        for tmp_dir in tmp_dirs:
            try:
                shutil.rmtree(os.path.join(cache_dir, tmp_dir),
                              ignore_errors=True)
            except Exception as err:
                _logger.warning('Deletion of old tmp dir "%s" failed: %s',
                                tmp_dir, err2unicode(err))
            time.sleep(0.001)
        _logger.debug('Clean of old tmp dir completed.')

    t = threading.Thread(target=_remove_tmp_dir_thread, args=(tmp_dirs,),
                         name='Migration: tmp dir deletion')
    t.daemon = True
    t.start()


def _get_tmp_dir():
    """get a temporary directory. The directory is created at fist call."""
    global _tmp_dir

    if not _tmp_dir:

        # NOTE: must be called before 'mkdtemp' for avoid deleting the current
        # tmp folder.
        _migration_remove_tmp_folders()

        try:
            _tmp_dir = tempfile.mkdtemp(dir=get_cache_dir())
        except:
            _logger.exception('Error when creating tmp dir for encryption '
                              'files')
            raise
        atexit.register(_clean_tmp)
    return _tmp_dir


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
