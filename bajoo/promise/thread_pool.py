# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor as Executor
from . import Deferred


class ThreadPoolExecutor(object):
    """Execute callables asynchronously on demand, in another threads."""

    def __init__(self, max_workers):
        """Initialize the thread pool

        Args:
            max_workers: The maximum number of threads that can be used to
                execute the given calls.
        """
        self._executor = Executor(max_workers)

    def submit(self, callback, *args, **kwargs):
        """Schedule the callable to be executed and return a Promise.

        Args:
            callback (callable): callback who will run in another thread.
            *args: argument passed to callback.
            **kwargs: keywords arguments passed to callback.
        Returns:
            Promise: Promise who resolve after the callback has been executed.
                It's fulfilled with the value returned by the callback.
                If the callback raise an exception, the promise is rejected
                with this exception.
        """
        df = Deferred()

        def on_future_done(f):
            try:
                df.resolve(f.result())
            except BaseException as error:
                df.reject(error)

        f = self._executor.submit(callback, *args, **kwargs)
        f.add_done_callback(on_future_done)

        return df.promise
