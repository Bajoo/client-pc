# -*- coding: utf-8 -*-


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
