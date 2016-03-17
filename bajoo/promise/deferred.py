
from .promise import Promise


class Deferred(object):
    """

    A Deferred is the "creator" side of an async task, whereas a Promise
    represents the asynchronous value from the "consumer" side.

    Attributes:
        promise (Promise): the Promise associated to the Deferred.
        resolve (function)
        reject (function)
    """

    def __init__(self, *args, **kwargs):
        self.promise = Promise(self._executor, *args, **kwargs)

    def _executor(self, resolve, reject):
        self.resolve = resolve
        self.reject = reject
