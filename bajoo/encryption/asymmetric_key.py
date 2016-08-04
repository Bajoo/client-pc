# -*- coding: utf-8 -*-

import logging
import tempfile
from .errors import EncryptionError

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
            key_file (FileStream): File-like object containing a key.
            main_context (boolean): If True, the global GPG context is used.
                Otherwise, a temporary, dedicated context is created.
        """
        from . import _get_gpg_context

        # TODO: It should use a temporary GPG context if main_context is False.
        context = _get_gpg_context()

        with key_file:
            content = key_file.read()
            import_result = context.import_keys(content)

            # TODO this code is for compatibility backward, to remove
            # as soon as every key encoded in a such way will be removed
            # from the server
            if import_result.count == 0:
                try:
                    content = content.decode('utf-8').encode('latin-1')
                except UnicodeError:
                    pass  # That's not a old-format key.
                else:
                    import_result = context.import_keys(content)

            # GPG messages and behavior are rather cryptic. By example, there
            # is a case when result.count == 0, but result.imported == 1
            # "import_result.results" contains one line per error or success.
            for result in import_result.results:
                problem = result.get('problem', None)
                if problem:
                    _logger.warning(
                        'Problem during import of GPG key: %s: %s',
                        result.problem_reason.get(problem, problem),
                        problem.get('text'))

            if not import_result.count:
                raise EncryptionError(
                    'key import Failed: %s' % import_result.summary(),
                    import_result.results)
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
        key_file.write(content)
        key_file.seek(0)
        return key_file
