# -*- coding: utf-8 -*-

"""Provides functions to encrypt and decrypt files asynchronously.

The encryption module is an interface using the GPG executable.
It supports two main features:
- The encryption and decryption of arbitrary files.
- The creation and use of asymmetric GPG keys.

The initialisation of GPG, must be done in two steps:
 - Using the Context() to initialize th encryption service.
 - setting the gpg home dir (see `set_gpg_home_dir()`).
A global keyring is instantiated (and kept between executions), for storing
keys regularly used.

All the heavy operations are executed asynchronously in another process, and
uses ``Promise`` instances to communicate the result.
"""

import errno
from functools import partial
import io
import logging
import os.path
from ..gnupg import GPG

from ..promise import reduce_coroutine
from .asymmetric_key import AsymmetricKey
from .errors import EncryptionError, KeyGenError, PassphraseError
from .errors import PassphraseAbortError
from .task_executor import TaskExecutor
from .process_transmission import wrap_file
from . import gpg_operations

_logger = logging.getLogger(__name__)

_executor = None

# main GPG() instance
_gpg = None
_gpg_home_dir = None


class Context(object):
    """Must be called before any GPG task."""

    def __enter__(self):
        global _executor

        _executor = TaskExecutor()
        _executor.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _executor

        if _executor:
            _executor.stop()
        _executor = None


def stop():
    global _executor

    if _executor:
        _executor.stop()
    _executor = None


def _get_gpg_context():
    """Initialize the GPG main keyring."""
    global _gpg

    if not _gpg:
        try:
            _gpg = GPG(verbose=False, gnupghome=_gpg_home_dir, use_agent=False)
        except (IOError, OSError) as e:
            _logger.exception("GPG() can't be initialized")
            if e.errno == errno.ENOENT:
                raise EncryptionError('GPG binary executable not found.')
            raise
        _gpg.encoding = 'utf-8'
    return _gpg


def _patch_remove_path(method, path, *args, **kwargs):
    ret = method(*args, **kwargs)
    try:
        os.remove(path)
    except (IOError, OSError) as e:
        if getattr(e, 'errno', None) == 2:
            # the file doesn't exists. It's happens when the file is "closed"
            # twice or more.
            pass
        else:
            _logger.warning('Unable to delete tmp file: %s' % path,
                            exc_info=True)
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


def set_gpg_home_dir(gpg_home_dir):
    """Set, or change, the GPG homedir path.

    This function MUST be called before any use of this module !

    If there is already a GPG instance, it will be replaced by a new one.

    Args:
        _gpg_home_dir (unicode):
    """
    global _gpg, _gpg_home_dir
    _gpg = None
    _gpg_home_dir = gpg_home_dir
    _get_gpg_context()


@reduce_coroutine()
def create_key(email, passphrase, container=False):
    """Generate a new GPG key.

    Returns:
        Future<AsymmetricKey>
    """
    _logger.debug('Start to generate a new GPG key ...')
    gpg = _get_gpg_context()

    args = {'key_length': 2048, 'name_email': email.encode('utf-8')}

    # Note: giving an argument passphrase=None to gen_key_input() will create a
    # passphrase 'None'. We must not pass the argument if we don't want a
    # passphrase.
    if passphrase is not None:
        args['passphrase'] = passphrase.encode('utf-8')

    if container:
        args['name_comment'] = 'Bajoo container key'
    else:
        args['name_comment'] = 'Bajoo user key'

    data = yield _executor.execute_task(gpg_operations.gen_key, gpg, **args)

    if not data:
        raise KeyGenError('Key generation failed: %s' % data)

    _logger.info('New GPG key created: %s', data.fingerprint)
    yield AsymmetricKey(gpg, data.fingerprint)


@reduce_coroutine()
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

    with source:
        if len(recipients) == 1:
            context = recipients[0]._context
        else:
            context = _gpg
            for key in recipients:
                import_key(key)

        dst_path = yield _executor.execute_task(gpg_operations.encrypt,
                                                context,
                                                wrap_file(source),
                                                recipients)

        result_file = io.open(dst_path, mode='rb')
        _patch_autodelete_file(result_file, dst_path)
        yield result_file


@reduce_coroutine()
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

    with source:
        passphrase = None
        if _retry > 0 and passphrase_callback:
            # The call to GPG without callback has failed; We retry with a
            # passphrase.
            passphrase = passphrase_callback(_retry > 1)
            if passphrase is None:
                # The user has refused to give his passphrase.
                raise PassphraseAbortError()

        try:
            dst_path = yield _executor.execute_task(gpg_operations.decrypt,
                                                    context,
                                                    wrap_file(source),
                                                    passphrase=passphrase)
        except PassphraseError:
            if passphrase_callback and _retry <= 4:
                source.seek(0)
                yield decrypt(source, key,
                              passphrase_callback=passphrase_callback,
                              _retry=_retry+1)
                return
            raise
        result_file = io.open(dst_path, mode='rb')
        _patch_autodelete_file(result_file, dst_path)
        yield result_file


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
