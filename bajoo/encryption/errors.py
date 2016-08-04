# -*- coding: utf-8 -*-

from ..common.i18n import N_


class EncryptionError(Exception):
    """Base class for all encryption-related errors."""
    pass


class KeyGenError(EncryptionError):
    """Exception raised by the failed generation of a GPG key"""
    pass


class EncryptError(EncryptionError):
    """Exception raised during a file encryption."""
    pass


class DecryptError(EncryptionError):
    """Exception raised during a file decryption."""
    pass


class PassphraseError(EncryptionError):
    """Invalid or missing passphrase"""
    pass


class PassphraseAbortError(EncryptionError):
    """Exception raised when the user refuse to give his passphrase."""

    def __init__(self):
        EncryptionError.__init__(
            self, N_('The passphrase request has been rejected by the user.'))
