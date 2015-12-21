# -*- coding: utf-8 -*-

import warnings
from bajoo.common import strings


class TestStrings(object):

    all_strings = [
        b'simple bytes string',
        u'bytes string with unicode ⚘ character'.encode('utf-8'),
        u'simple unicode string',
        u'unicode string with unicode ⚘ character'
    ]

    unicode_type = type(u'unicode')

    def test_to_str(self):
        for msg in self.all_strings:
            result = strings.to_str(msg)
            assert isinstance(result, str)

    def test_to_unicode(self):
        for msg in self.all_strings:
            result = strings.to_unicode(msg)
            assert isinstance(result, self.unicode_type)

    def test_to_bytes(self):
        for msg in self.all_strings:
            result = strings.to_bytes(msg)
            assert isinstance(result, bytes)

    def test_to_str_with_specific_input_encoding(self):
        latin_1_bytes = u'ééé'.encode('latin-1')
        result = strings.to_str(latin_1_bytes, in_enc='latin-1')
        assert result == 'ééé'

    def test_to_str_with_specific_output_encoding(self):
        latin_1_bytes = u'ééé'.encode('latin-1')
        result = strings.to_str('ééé', out_enc='latin-1')

        if str == bytes:
            assert result == latin_1_bytes
        else:
            assert result == 'ééé'

    def test_to_unicode_with_specific_input_encoding(self):
        encoded_bytes_msg = u'ééé'.encode('utf-16')
        result = strings.to_unicode(encoded_bytes_msg, in_enc='utf-16')
        assert result == u'ééé'

    def test_to_bytes_with_specific_input_encoding(self):
        encoded_bytes_msg = u'ééé'.encode('utf-7')
        result = strings.to_bytes(encoded_bytes_msg, in_enc='utf-7')
        assert result == u'ééé'.encode('utf-8')  # utf-8 is the default output.

    def test_to_bytes_with_specific_output_encoding(self):
        encoded_bytes_msg = u'message'.encode('utf-32')
        result = strings.to_bytes('message', out_enc='utf-32')
        assert result == encoded_bytes_msg

    def test_to_bytes_with_both_encoding_specified(self):
        encoded_bytes_msg = u'message'.encode('utf-16')
        result = strings.to_bytes(encoded_bytes_msg, in_enc='utf-16',
                                  out_enc='utf-32')
        assert result == u'message'.encode('utf-32')

    def test_ensure_unicode(self):
        with warnings.catch_warnings(record=True) as w:
            strings.ensure_unicode(u'unicode')
            assert len(w) == 0
            strings.ensure_unicode(b'bytes')
            assert len(w) == 1

    def test_ensure_str(self):
        with warnings.catch_warnings(record=True) as w:
            strings.ensure_str(u'unicode')
            strings.ensure_str(b'bytes')
            assert len(w) == 1

    def test_ensure_bytes(self):
        with warnings.catch_warnings(record=True) as w:
            strings.ensure_bytes(u'unicode')
            assert len(w) == 1
            strings.ensure_bytes(b'bytes')
            assert len(w) == 1
