# -*- coding: utf-8 -*-

import logging
from threading import Condition

_logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """An operation could not be executed within the time allowed."""
    pass


class Promise(object):
    """It represents an operation expected to be completed in the future.

    A Promise is used for asynchronous computation. It contains a value not yet
    known when the Promise is created. It allows to set callbacks who will be
    called as soon as the result is known. It's a "promise" of a future value.

    All calls to the methods are thread-safe.
    """

    PENDING = 'pending'
    FULFILLED = 'fulfilled'
    REJECTED = 'rejected'

    def __init__(self, executor):
        """Constructor of the Promise.

        Generate the two callbacks for the executor, then call the `executor`.
        It means the executor will be fully executed before the the constructor
        returns.
        If the executor raises an exception, it's caught and the Promise is
        rejected with this exception.

        Args:
            executor (callable): Takes 2 callable arguments:
                The first one, `on_filled()` should be called when the Promise
                is fulfilled (ie the tasks is done) and must accept the
                result's value as its only argument.
                The second, `on_rejected()`, should be called when an error
                occurs. Its argument must be an instance of `Exception`.
        """

        self._state = self.PENDING
        self._result = None
        self._error = None
        self._condition = Condition()

        self._callbacks = []
        self._errbacks = []

        def on_fulfilled(result):
            with self._condition:
                if self._state != self.PENDING:
                    _logger.warning('Try to fulfill Promise %s already '
                                    'settled. New result will be ignored: %s'
                                    % (repr(self), repr(result)))
                    return
                self._result = result
                self._state = self.FULFILLED

                self._condition.notify_all()
                # TODO: CALL CALLBACKS ...

        def on_rejected(error):
            with self._condition:
                if self._state != self.PENDING:
                    _logger.warning('Try to reject Promise %s already settled.'
                                    ' New error will be ignored: %s'
                                    % (repr(self), repr(error)))
                    return
                if not isinstance(error, Exception):
                    # Although it shouldn't happens, the non-exception value
                    # can be chained like any value. In case of call to
                    # result(), the Promise will raise a TypeError "Unable to
                    # throw non-exception value". The real error value will be
                    # lost, but anyway the caller will get an exception raised.
                    _logger.warning('Promise %s rejected with non-exception'
                                    'value: %s' % (repr(self), repr(error)))
                self._error = error
                self._state = self.REJECTED

                self._condition.notify_all()
                # TODO: CALL CALLBACK ...

        try:
            executor(on_fulfilled, on_rejected)
        except BaseException as error:
            on_rejected(error)

    def result(self, timeout=None):
        """Wait for the result and returns it as soon as it's available.

        Args:
            timeout (int, optional): if set, maximum time to wait the promise
                to be fulfilled. By default, it can wait indefinitely.
        Returns:
            *: value encapsulated, defined by the operation.
        Raises:
            TimeoutError: if the promise is not settled within the delay.
            *: If the promise is rejected, the rejection cause is raised.
        """
        with self._condition:
            if self._state == self.PENDING:
                self._condition.wait(timeout)

            if self._state == self.PENDING:
                raise TimeoutError()
            elif self._state == self.REJECTED:
                raise self._error
            else:
                return self._result

    def exception(self, timeout=None):
        """Wait for the promise rejection and returns it's error.

        Args:
            timeout (int, optional): if set, maximum time to wait the promise
                to be rejected. By default, it can wait indefinitely.
        Returns:
            Exception: the error causing the rejection of the Promise.
            None: if the promise is fulfilled.
        Raises:
            TimeoutError: if the promise is not settled within the delay.
            *: If the promise is rejected, the rejection cause is raised.
        """

        with self._condition:
            if self._state == self.PENDING:
                self._condition.wait(timeout)

            if self._state == self.PENDING:
                raise TimeoutError()
            else:
                return self._error
