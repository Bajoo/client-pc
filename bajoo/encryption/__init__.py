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

import atexit
from concurrent.futures import ThreadPoolExecutor
import errno
from functools import partial
import io
import logging
from multiprocessing import cpu_count
import os.path
import tempfile
from gnupg import GPG

from ..common.path import get_data_dir, get_cache_dir
from ..common.future import then
from .asymmetric_key import AsymmetricKey
from .errors import EncryptionError, KeyGenError, EncryptError, DecryptError
from .errors import PassphraseAbortError

_logger = logging.getLogger(__name__)


_thread_pool = ThreadPoolExecutor(max_workers=cpu_count())

# main GPG() instance
_gpg = None

_tmp_dir = None
try:
    _tmp_dir = tempfile.mkdtemp(dir=get_cache_dir())
except:
    _logger.warning('Error when creating tmp dir for encryption files',
                    exc_info=True)
    pass


@atexit.register
def _clean_tmp():
    global _tmp_dir
    try:
        os.removedirs(_tmp_dir)
        _tmp_dir = None
    except:
        pass


def _get_gpg_context():
    """Initialize the GPG main keyring."""
    global _gpg

    if not _gpg:
        gpg_home = os.path.join(get_data_dir(), 'gpg')
        try:
            _gpg = GPG(verbose=False, gnupghome=gpg_home, use_agent=False)
        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                raise EncryptionError('GPG binary executable not found.')
            raise
    return _gpg


def _patch_remove_path(method, path, *args, **kwargs):
    ret = method(*args, **kwargs)
    try:
        os.remove(path)
    except (IOError, OSError):
        _logger.warning('Unable to delete tmp file: %s' % path, exc_info=True)
    return ret


def _patch_autodelete_file(file_stream, path):
    """Patch the file-like object, so it will remove the file on close.

    Args:
        file_stream (File-like): object to patch
        path (str): path of the file to remove.
    """

    if file_stream.close is not file_stream.__exit__:
        file_stream.close = partial(_patch_remove_path, file_stream.close,
                                    path)
    file_stream.__exit__ = partial(_patch_remove_path, file_stream.__exit__,
                                   path)


def create_key(email, passphrase, container=False):
    """Generate a new GPG key.

    Returns:
        Future<AsymmetricKey>
    """
    _logger.debug('Start to generate a new GPG key ...')
    gpg = _get_gpg_context()

    args = {'key_length': 2048, 'name_email': email}

    # Note: giving an argument passphrase=None to gen_key_input() will create a
    # passphrase 'None'. We must not pass the argument if we don't want a
    # passphrase.
    if passphrase is not None:
        args['passphrase'] = passphrase

    if container:
        args['name_comment'] = 'Bajoo container key'
    else:
        args['name_comment'] = 'Bajoo user key'

    input_data = gpg.gen_key_input(**args)
    f = _thread_pool.submit(gpg.gen_key, input_data)

    def on_key_generated(data):
        _logger.info('New GPG key created: %s', data.fingerprint)
        if not data:
            raise KeyGenError('Key generation failed: %s' % data)
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
            resulting encrypted data. The file will be erased from the disk as
            soon as it will be closed.
    """

    # If 'source' is a filename, open it
    try:
        if isinstance(source, basestring):
            source = io.open(source, 'rb')
    except NameError:
        if isinstance(source, str):
            source = io.open(source, 'rb')

    def close_source(result):
        source.close()
        return result

    def close_source_err(error):
        source.close()
        raise error

    try:
        if len(recipients) == 1:
            context = recipients[0]._context
        else:
            context = _gpg
            for key in recipients:
                import_key(key)

        with tempfile.NamedTemporaryFile(delete=False, dir=_tmp_dir) as tf:
            dst_path = tf.name

        f = _thread_pool.submit(context.encrypt_file, source,
                                [key.fingerprint for key in recipients],
                                output=dst_path,
                                armor=False, always_trust=True)

        def _on_file_encrypted(result):
            if not result:
                raise EncryptError('Encryption failed', result)
            result_file = io.open(dst_path, mode='rb')
            _patch_autodelete_file(result_file, dst_path)
            return result_file

        f = then(f, _on_file_encrypted)
        f.then(close_source, close_source_err)
        return f
    except:
        source.close()
        raise


def decrypt(source, key=None, passphrase_callback=None, _retry=0):
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
        passphrase_callback (callable, optional): If set, this callback will
            be used to retrieve the passphrase. This callback takes a boolean
            argument 'is_retry' (if the callback has already been called for
            this operation before), and returns either a string or None (if the
            user don't want to give his passphrase).
        _retry (int): number of passphrase attempt already done (and failed).
    Returns:
        Future<TemporaryFile>: A Future returning a temporary file of the
            resulting decrypted data. The file will be erased from the disk as
            soon as it will be closed.
    """

    if key:
        context = key._context
    else:
        context = _gpg
    # If 'source' is a filename, open it
    try:
        if isinstance(source, basestring):
            source = io.open(source, 'rb')
    except NameError:
        if isinstance(source, str):
            source = io.open(source, 'rb')

    def close_source(result):
        source.close()
        return result

    def close_source_err(error):
        source.close()
        raise error

    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=_tmp_dir) as tf:
            dst_path = tf.name

        passphrase = None
        if _retry > 0 and passphrase_callback:
            # The call to GPG without callback has failed; We retry with a
            # passphrase.
            passphrase = passphrase_callback(_retry > 1)
            if passphrase is None:
                # The user has refused to give his passphrase.
                raise PassphraseAbortError()

        f = _thread_pool.submit(context.decrypt_file, source, output=dst_path,
                                passphrase=passphrase)

        def on_file_decrypted(result):
            if not result:
                # pkdecrypt codes are defined in libgpg-error (in err-codes.h)
                if '[GNUPG:] ERROR pkdecrypt_failed 11' in result.stderr \
                        or '[GNUPG:] MISSING_PASSPHRASE' in result.stderr:
                    if passphrase_callback and _retry <= 4:
                        source.seek(0)
                        return decrypt(source, key,
                                       passphrase_callback=passphrase_callback,
                                       _retry=_retry+1)
                    elif '[GNUPG:] MISSING_PASSPHRASE' in result.stderr:
                        raise DecryptError('Decryption failed: '
                                           'missing passphrase')
                    else:
                        raise DecryptError('Decryption failed: probably a bad'
                                           'passphrase')
                raise DecryptError('Decryption failed: %s' % result.status)

            result_file = io.open(dst_path, mode='rb')
            _patch_autodelete_file(result_file, dst_path)
            return result_file

        f = then(f, on_file_decrypted)
        f = f.then(close_source, close_source_err)
        return f
    except:
        source.close()
        raise


def import_key(key):
    """Add a key to the global Bajoo keyring.

    The key will be saved on the disk, and will be available for any GPG
    operation. It will persists between executions of the program.

    Args:
        key (AsymmetricKey): key to add to the global Bajoo keyring.
    """
    key_buffer = b''

    with key.export(secret=True) as key_content:
        key_buffer += key_content.read()

    _gpg.import_keys(key_buffer)


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
