# -*- coding: utf-8 -*-

from ..promise import CancelledError, is_cancellable


class RequestPromise(object):
    """
    This is a proxy class for promise.Promise
    which enables cancelling the long requests
    via a shared_data object.
    """

    def __init__(self, promise, shared_data):
        """
        Create a RequestFuture.

        Args:
            future: (promise.Promise) the promise returned by the thread pool
                when we submit/map a new task.
            shared_data: (dict) the object containing shared resource
                between this promise and the task executing thread.
                It must have a boolean item 'cancelled'.
        """
        self._promise = promise
        self._shared_data = shared_data

    def __getattr__(self, name):
        return getattr(self._promise, name)

    def cancel(self):
        """
        Cancel the request via the shared object.
        """
        if not is_cancellable(self._promise) or not self._promise.cancel():
            self._shared_data['cancelled'] = True

    def result(self, timeout=None):
        """
        Get the request's result.
        """
        if self._shared_data['cancelled']:
            raise CancelledError

        return self._promise.result(timeout)
