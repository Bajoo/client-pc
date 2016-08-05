# -*- coding: utf-8 -*-

import io
import hashlib
import tempfile


class BadSizeException(Exception):
    """Raised when input file-object size don't match the expected size.

    It can happens when the File-Object fetch data from a network socket and
    the socket is closed.
    """
    def __init__(self, received, expected):
        Exception.__init__(self)
        self.received = received
        self.expected = expected

    def __str__(self):
        return '%s(received=%s, expected=%s)' % (self.__class__.__name__,
                                                 self.received, self.expected)

    __repr__ = __str__


class BadMd5SumException(Exception):
    """Raised when input file-object control sum don't match the expected sum.

    If it happens, the file must be considered as corrupted.
    """
    def __init__(self, received, expected):
        Exception.__init__(self)
        self.received = received
        self.expected = expected

    def __str__(self):
        return '%s(received=%s, expected=%s)' % (self.__class__.__name__,
                                                 self.received, self.expected)

    __repr__ = __str__


class ChunkData(object):
    """Abstract piece of data.

    All File-like objects and streams manipulated by this class must be in
    binary mode.

    Attributes:
        file (File Object): File-like object, containing the data.
        total_size (int): if set, total data size, including the content not
            yet loaded.
        partial_size (int): size size of the data actually stored.
        md5_sum (str): if set, md5 sum of the full data, including content not
            yet loaded.
        partial_md5_sum (str): md5 sum of the data actually stored.
    """

    CHUNK_SIZE = 16 * 1024
    MAX_BUFFER_SIZE = 512 * 1024

    def __init__(self, file_obj, hint_size=None, hint_md5=None):
        """Create a ChunkData from a file-like object, by copying its content.

        Args:
            file_obj ():
            hint_size (int, optional): If set, total size expected. This value
                is used to check that the file_obj has been fully read without
                problems (especially closed socket), and to determine the best
                way to store the data (in memory or written on disk).
            hint_md5 (str, optional): If set, md5 sum of the full content.
        Except:
            BadSizeException: raised if hint_size is set, and the total size
                read from the source don't match the hint.
            BadMd5SumException: raised if hint_md5 is set, but don't match with
                the real md5.
        """

        self.total_size = int(hint_size) if hint_size else None
        self.md5_sum = hint_md5
        self.partial_size = 0
        self._partial_md5_hash = None  # instance of hashlib.HASH
        self.file = None

        if hint_size:
            if int(hint_size) < self.MAX_BUFFER_SIZE:
                self.file = io.BytesIO()
            else:
                self.file = tempfile.TemporaryFile(suffix=".tmp")
        else:
            self.file = tempfile.SpooledTemporaryFile(
                max_size=self.MAX_BUFFER_SIZE, suffix=".tmp")

        self._copy_from(file_obj)
        if not self.total_size:
            self.total_size = self.partial_size

        if self.partial_size != self.total_size:
            raise BadSizeException(received=self.partial_size,
                                   expected=self.total_size)

        if self.md5_sum and self.partial_md5_sum != self.md5_sum:
            assert self.partial_md5_sum == self.md5_sum
            raise BadMd5SumException(received=self.md5_sum,
                                     expected=self.md5_sum)

        self.file.seek(0)

    @property
    def partial_md5_sum(self):
        return self._partial_md5_hash.hexdigest()

    def _copy_from(self, file_obj):
        """Read file_obj and copy it into self.file"""

        self._partial_md5_hash = hashlib.md5()

        while True:
            chunk = file_obj.read(self.CHUNK_SIZE)
            if not chunk:
                break

            self.file.write(chunk)
            self._partial_md5_hash.update(chunk)
            self.partial_size += len(chunk)
