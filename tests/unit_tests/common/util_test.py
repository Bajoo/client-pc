#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.common.util import human_readable_bytes, xor

"""### TEST CASES ###
    human_readable_bytes with everyt units
    human_readable_bytes over limit

    TODO open_folder It opens a file browser, how to check that ?

    xor data
        data and key are bytes, same size
        data and key not are not bytes, same size
        data and key are bytes, key is bigger
        data and key are bytes, key is shorter
"""


class TestHuman_readable_bytes(object):

    def test_123B(self):
        assert "123 B" == human_readable_bytes(123)

    def test_123KB(self):
        assert "120.56 KB" == human_readable_bytes(123456)

    def test_123MB(self):
        assert "117.74 MB" == human_readable_bytes(123456789)

    def test_123GB(self):
        assert "114.98 GB" == human_readable_bytes(123456789123)

    def test_123TB(self):
        assert "112.28 TB" == human_readable_bytes(123456789123456)

    def test_123PB(self):
        assert "109.65 PB" == human_readable_bytes(123456789123456789)

    def test_123EB(self):
        assert "107.08 EB" == human_readable_bytes(123456789123456789123)

    def test_123ZB(self):
        assert "104.57 ZB" == human_readable_bytes(123456789123456789123456)

    def test_123YB(self):
        assert "102.12 YB" == human_readable_bytes(123456789123456789123456789)

    def test_123456YB(self):
        assert "102121.06 YB" == human_readable_bytes(
            123456789123456789123456789123)


class TestXor(object):

    def test_not_byte_same_size(self):
        assert xor("0123456789ABCDEF", "FEDCBA9876543210") \
            == b'vtvpvt\x0f\x0f\x0f\x0ftvpvtv'

    def test_byte_same_size(self):
        string1 = "0123456789ABCDEF"
        string2 = "FEDCBA9876543210"
        assert xor(bytes(string1.encode('utf-8')),
                   bytes(string2.encode('utf-8'))) \
            == b'vtvpvt\x0f\x0f\x0f\x0ftvpvtv'

    def test_byte_key_is_bigger(self):
        string1 = "0123456789ABCDEF"
        string2 = "FEDCBA9876543210FEDCBA"
        assert xor(bytes(string1.encode('utf-8')),
                   bytes(string2.encode('utf-8'))) \
            == b'vtvpvt\x0f\x0f\x0f\x0ftvpvtv'

    def test_byte_key_is_shorter(self):
        string1 = "0123456789ABCDEF"
        string2 = "FEDCBA98"
        assert xor(bytes(string1.encode('utf-8')),
                   bytes(string2.encode('utf-8'))) \
            == b'vtvpvt\x0f\x0f~|\x05\x01\x01\x05|~'

    def test_mixUnicodeWithItself(self):
        string = u'simple unicode string'
        result = xor(string, string)

        if isinstance(string, bytes):
            assert xor(result, string) == string
        else:
            assert xor(result, string) == string.encode('utf-8')

    def test_mixUnicodeWithStrangeUnicode(self):
        string1 = u'simple unicode string'
        string2 = u'unicode string with unicode charaters: ❄'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixUnicodeWithByteString(self):
        string1 = u'simple unicode string'
        string2 = b'bytes string'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixUnicodeWithComplexByteString(self):
        string1 = u'simple unicode string'
        string2 = b'complex bytes string: \x99 \xff \x00'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixStrangeUnicodeWithItself(self):
        string = u'unicode string with unicode charaters: ❄'
        result = xor(string, string)

        if isinstance(string, bytes):
            assert xor(result, string) == string
        else:
            assert xor(result, string) == string.encode('utf-8')

    def test_mixStrangeUnicodeWithByteString(self):
        string1 = u'unicode string with unicode charaters: ❄'
        string2 = b'bytes string'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixStrangeUnicodeWithComplexByteString(self):
        string1 = u'unicode string with unicode charaters: ❄'
        string2 = b'complex bytes string: \x99 \xff \x00'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixByteStringWithItself(self):
        string = b'bytes string'
        result = xor(string, string)

        if isinstance(string, bytes):
            assert xor(result, string) == string
        else:
            assert xor(result, string) == string.encode('utf-8')

    def test_mixByteStringWithComplexByteString(self):
        string1 = b'bytes string'
        string2 = b'complex bytes string: \x99 \xff \x00'
        result = xor(string1, string2)

        if isinstance(string1, bytes):
            assert xor(result, string2) == string1
        else:
            assert xor(result, string2) == string1.encode('utf-8')

        result = xor(string2, string1)
        if isinstance(string2, bytes):
            assert xor(result, string1) == string2
        else:
            assert xor(result, string1) == string2.encode('utf-8')

    def test_mixComplexByteStringWithItself(self):
        string = b'complex bytes string: \x99 \xff \x00'
        result = xor(string, string)

        if isinstance(string, bytes):
            assert xor(result, string) == string
        else:
            assert xor(result, string) == string.encode('utf-8')
