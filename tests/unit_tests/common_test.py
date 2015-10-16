# -*- coding: utf8 -*-

from itertools import product

from bajoo.common.util import xor


class TestUtil(object):
    """Test of the bajoo.common.util module"""

    def test_xor_unicode(self):
        """Try the xor() function using mix of unicode and bytes inputs."""
        all_strings = [
            u'simple unicode string',
            u'unicode string with unicode charaters: ❄',
            b'bytes string',
            b'complex bytes string: \x99 \xff \x00'
        ]
        for key, value in product(all_strings, repeat=2):
            result = xor(value, key)
            if isinstance(value, bytes):
                assert xor(result, key) == value
            else:
                assert xor(result, key) == value.encode('utf-8')
