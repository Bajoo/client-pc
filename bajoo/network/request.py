# -*- coding: utf-8 -*-

import functools
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


@functools.total_ordering
class Request(object):
    """Represents a request waiting to be executed.

    Attributes:
        action (str): one of 'UPLOAD', 'DOWNLOAD', 'JSON' or 'PING'. Set how to
            handle upload and download.
        verb (str): HTTP verb
        url (str): HTTP URL
        params (dict, optional):
        source (str / File-like): if action is 'UPLOAD', source file.
            It can be a File-like object (in which case it will be send as is),
            or a str containing the path of the file to send.
        priority (int): Request priority. requests of lower priority
            are executed first. Default to 100.
        increment_id (int): unique ID set when the request is added to the
            queue. It's used as in comparison to find which requests must be
            prioritized: at equal priority, first-created requests (ie, with a
            smaller increment_id) are executed first.
    """

    UPLOAD = 'UPLOAD'
    DOWNLOAD = 'DOWNLOAD'
    JSON = 'JSON'
    PING = 'PING'

    def __init__(self, action, verb, url,
                 params=None, source=None, priority=100):
        self.action = action
        self.verb = verb
        self.url = url
        self.params = params or {}
        self.source = source
        self.priority = priority
        self.increment_id = None

    def __str__(self):
        return '%s (%s) %s' % (self.verb, self.action, self.url)

    def __eq__(self, other):
        return (self.priority == other.priority and
                self.increment_id == other.increment_id)

    def __lt__(self, other):
        return ((self.priority, self.increment_id) <
                (other.priority, other.increment_id))

    @property
    def host(self):
        return urlparse(self.url).netloc

    @property
    def scheme(self):
        return urlparse(self.url).scheme
