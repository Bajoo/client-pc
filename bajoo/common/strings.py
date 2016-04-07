# -*- coding: utf-8 -*-

import warnings


# _unicode_type is portable Python2 and Python3
_unicode_type = type(u'unicode')
warnings.simplefilter('always', UnicodeWarning)


def _check_type_expectation(value, expected_type):
    if not expected_type or isinstance(value, expected_type):
        return

    expected_type_str = expected_type.__name__
    value_type_str = type(value).__name__
    message = '%s string type was expected. Instead, got %s' \
              % (expected_type_str, value_type_str)
    warnings.warn(message, UnicodeWarning, stacklevel=2)


def to_str(input_str, expected_type=None, in_enc='utf-8',
           out_enc='utf-8'):
    """Convert an input string (of type 'bytes' or 'unicode') in type 'str'

    The 'str' type is 'unicode' in Python 3 and 'bytes' in Python 2

    Args:
        input_str (bytes/unicode): input value.
        expected_type (type, optional): expected input type. If the type
            doesn't match, a warning is raised.
        in_enc (str, optional): input encoding (if the input is bytes)
        out_enc (str, optional): output encoding (if the output is bytes)
    Returns:
        str: the input value, converted in 'str' if needed.
    """

    _check_type_expectation(input_str, expected_type)
    if isinstance(input_str, str):
        if str == bytes:
            return input_str.decode(in_enc).encode(out_enc)
        else:
            return input_str

    if str == bytes:
        return to_bytes(input_str, in_enc=in_enc, out_enc=out_enc)
    else:
        return to_unicode(input_str, in_enc=in_enc)


def to_unicode(input_str, expected_type=None, in_enc='utf-8'):
    """Convert an input string (of type 'bytes' or 'unicode') in type 'unicode'

    Args:
        input_str (bytes/unicode): input value.
        expected_type (type, optional): expected input type. If the type
            doesn't match, a warning is raised.
        in_enc (str, optional): input encoding (if the input is bytes)
    Returns:
        unicode: the input value, converted in unicode if needed.
    """
    _check_type_expectation(input_str, expected_type)
    if isinstance(input_str, _unicode_type):
        return input_str

    return input_str.decode(in_enc)


def to_bytes(input_str, expected_type=None, in_enc='utf-8',
             out_enc='utf-8'):
    """Convert the input string (of type 'bytes' or 'unicode') in type 'bytes'

    Args:
        input_str (bytes/unicode): input value.
        expected_type (type, optional): expected input type. If the type
            doesn't match, a warning is raised.
        in_enc (str, optional): input encoding (if the input is bytes)
        out_enc (str, optional): output encoding
    Returns:
        bytes: the input value, converted in bytes if needed.
    """

    _check_type_expectation(input_str, expected_type)

    if isinstance(input_str, bytes):
        return input_str.decode(in_enc).encode(out_enc)

    return input_str.encode(out_enc)


def ensure_unicode(input_str, in_enc='utf-8'):
    """Ensures the string value is of type unicode.

    If the input type doesn't match the expected type, a warning is raised and
    the value is converted.

    Args:
        input_str (bytes/unicode): input value. Should be an unicode value.
        in_enc (str, optional): input encoding (if the input is bytes)
    Returns:
        unicode: the input value, converted in unicode if needed.
    """
    return to_unicode(input_str, expected_type=_unicode_type, in_enc=in_enc)


def ensure_str(input_str, in_enc='utf-8', out_enc='utf-8'):
    """Ensures the string value is of type str.

    If the input type doesn't match the expected type, a warning is raised and
    the value is converted.

    Args:
        input_str (bytes/unicode): input value. Should be a "str".
        in_enc (str, optional): input encoding (if input is bytes)
        out_enc (str, optional): output encoding (if output is bytes)
    Returns:
        str: the input value, converted in type 'str' if needed.
    """
    return to_str(input_str, expected_type=str, in_enc=in_enc, out_enc=out_enc)


def ensure_bytes(input_str, in_enc='utf-8', out_enc='utf-8'):
    """Ensures the string value is of type bytes.

    If the input type doesn't match the expected type, a warning is raised and
    the value is converted.

    Args:
        input_str (bytes/unicode): input value. Should be a bytes.
        in_enc (str, optional): input encoding (if input is bytes)
        out_enc (str, optional): output encoding
    Returns:
        bytes: the input value, converted in bytes if needed.
    """
    return to_bytes(input_str, expected_type=bytes, in_enc=in_enc,
                    out_enc=out_enc)
