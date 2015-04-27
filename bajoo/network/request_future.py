# -*- coding: utf-8 -*-
from futures import CancelledError


class RequestFuture(object):
    """
    This is a proxy class for futures.Future
    which enables cancelling the long requests
    via a shared_data object.
    """

    def __init__(self, future, shared_data):
        """
        Create a RequestFuture.

        Args:
            future: (futures.Future) the future returned by the thread pool
                when we submit/map a new task.
            shared_data: (dict) the object containing shared resource
                between this future and the task executing thread.
                It must have a boolean item 'cancelled'.
        """

        self._future = future
        self._shared_data = shared_data

    def __getattr__(self, name):
        return getattr(self._future, name)

    def cancel(self):
        """
        Cancel the request via the shared object.
        """
        if not self._future.cancel():
            self._shared_data['cancelled'] = True

    def cancelled(self):
        return self._future.cancelled() or self._shared_data['cancelled']

    def result(self):
        """
        Get the request's result.
        """
        if self._shared_data['cancelled']:
            raise CancelledError

        return self._future.result()
