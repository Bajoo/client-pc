# -*- coding: utf-8 -*-

import io
import logging
import os
import tempfile
# from gnupg import GPG


_logger = logging.getLogger(__name__)


class AsymmetricKey(object):
    """Asymmetric GPG key

    Attributes:
        fingerprint (str): fingerprint of the key.
    """

    def __init__(self, gpg_context, fingerprint):
        """Instance of the GPG key from the keyring and its fingerprint."""
        self._context = gpg_context
        self.fingerprint = fingerprint

    @classmethod
    def load(cls, key_file, main_context=False):
        """Load the AsymmetricKey

        Args:
            key_file (str|FileStream): if it's a str, path of the file
                containing the key. If it's a File-like object, content of the
                key.
            main_context (boolean): If True, the global GPG context is used.
                Otherwise, a temporary, dedicated context is created.
        """
        from . import _get_gpg_context

        # TODO: folder GPG key should not be added in the keyring.
        # if main_context:
        context = _get_gpg_context()
        # else:
        #    # TODO: find a better way to create this temporary file.
        #    with tempfile.NamedTemporaryFile(delete=False) as tf:
        #        tmp_file = tf.name
        # context = GPG(verbose=False, gnupghome='./tmp_keyring',
        #               keyring=tmp_file)

        try:
            if isinstance(key_file, basestring):
                key_file = io.open(key_file, 'rb')
        except NameError:
            if isinstance(key_file, str):
                key_file = io.open(key_file, 'rb')
        with key_file:
            content = key_file.read().decode('utf-8')
            import_result = context.import_keys(content)

            if not import_result.count:
                # >>> print(import_result.results)
                # [{'text': 'No valid data found', 'problem': '0',
                #  'fingerprint': None}]
                pass  # TODO: raise exception
            if import_result.count > 1:
                _logger.warning('GPG key file contains more than one key: %s',
                                import_result.fingerprints)
            return cls(context, import_result.fingerprints[0])

    def export(self, secret=False):
        """Export the key under the form of a file.

        Returns:
            TemporaryFile: representation of the key
        """
        key_file = tempfile.TemporaryFile()
        content = self._context.export_keys(self.fingerprint, armor=False,
                                            secret=secret)
        key_file.write(content.encode('utf-8'))
        key_file.seek(0)
        return key_file

    def __close__(self):
        """Delete the temporary keyring.

        All instances of AsymmetricKey MUST be closed after use.
        """
        if self._tmp_file:
            os.remove(self._tmp_file)
