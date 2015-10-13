# -*- coding: utf-8 -*-

import logging
from threading import Condition
from .util import is_thenable

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

    def __init__(self, executor, _name=None, _previous=None):
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
            _name (str): if set, name used when converted to text.
        """

        self._state = self.PENDING
        self._result = None
        self._error = None
        self._condition = Condition()
        self._name = _name or getattr(executor, '__name__', '???')
        self._previous = _previous

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

                for callback in self._callbacks:
                    self._exec_callback(callback, result)

                # Free the references
                self._callbacks = None
                self._errbacks = None

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

                for errback in self._errbacks:
                    self._exec_callback(errback, error, is_errback=True)

                # Free the references
                self._callbacks = None
                self._errbacks = None

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

    def then(self, on_fulfilled=None, on_rejected=None):
        """Create a new promise from callbacks called when this one is settled.

        If the promise is fulfilled, the `on_fullfilled` callback will be
        called. Otherwise (the promise has been rejected), the `on_rejected`
        callback is called.
        In any case, the callback will define the state of the returned
        Promise. If the callback raises an exception, the new Promise is
        rejected. The callback can returns:
        - A value: the new promise will be fulfilled with this value.
        - Another Promise, or any object with a `then` method: when fulfilled
            or rejected, will transfer its status (state and result/error) to
            the Promise returned by this method.

        If a callback is not defined, the state of the self promise" is
        transferred at the new promise (the state and the value/error).

        Args:
            on_fulfilled (callable, optional):  This callback will receive the
                result of the original promise as argument.
            on_rejected (callable, optional): This callback will receive the
                exception raised by the original promise as argument.
        Returns:
            Promise<*>: new promise depending of self.
        """

        def deferred_chained_promise(fulfilled, rejected):

            def callback(result):
                if on_fulfilled is None:
                    return fulfilled(result)
                else:
                    try:
                        new_result = on_fulfilled(result)
                    except BaseException as error:
                        return rejected(error)

                if is_thenable(new_result):
                    new_result.then(fulfilled, rejected)
                else:
                    fulfilled(new_result)

            def errback(error):
                if on_rejected is None:
                    return rejected(error)
                else:
                    try:
                        result = on_rejected(error)
                    except BaseException as new_error:
                        return rejected(new_error)

                if is_thenable(result):
                    result.then(fulfilled, rejected)
                else:
                    fulfilled(result)

            self._add_callback(callback)
            self._add_errback(errback)

        if not on_rejected:
            name = '%s' % getattr(on_fulfilled, '__name__', '???')
        elif not on_fulfilled:
            name = '<None, %s>' % getattr(on_rejected, '__name__', '???')
        else:
            name = '<%s, %s>' % (getattr(on_fulfilled, '__name__', '???'),
                                 getattr(on_fulfilled, '__name__', '???'))
        return Promise(deferred_chained_promise, _name=name, _previous=self)

    def catch(self, on_rejected):
        """Create a new promise with a callback called when an error occurs.

        Alias of `self.then(None, on_rejected)`

        Args:
            on_rejected (callable): Must take an argument instance of Exception
                (or one of its subclass). Will be called if `self` is rejected.
        returns:
            Promise<*>: new Promise chained to `self`. If `self` is fulfilled,
                the promised value will be the same as `self`. Otherwise, the
                value returned by the `on_rejected()` callback.
        """
        return self.then(None, on_rejected)

    def safeguard(self):
        """Catch all errors and log them with the most details possible.

        This method is aimed to protect the program from uncaught rejected
        Promise. If no error handler has been set (via then() or catch()), the
        default behavior is to do nothing, and thus, errors are silently
        ignored.
        Calling `safeguard()` after all chains are set will catch these errors,
        and log them as ERROR with the maximum of details possible.
        """
        def guard(error):
            try:
                raise error
            except:
                _logger.exception('[SAFEGUARD] %s' % self)

        self._add_errback(guard)

    def __str__(self):
        return 'Promise(%s)' % self._inner_print()

    def _inner_print(self):
        with self._condition:
            if self._state == self.REJECTED:
                state = 'R'
            elif self._state == self.FULFILLED:
                state = 'F'
            else:
                state = 'P'

        if self._previous:
            return '%s -> %s %s' % (self._previous._inner_print(), self._name,
                                    state)
        return '%s %s' % (self._name, state)

    @classmethod
    def resolve(cls, value):
        """Create a promise who resolves the selected value.

        Args:
            value: result of the promise. If it's a promise, it's returned as
                is.
        Returns:
            Promise: new Promise already fulfilled, containing the value
                passed in parameter.
        """
        if is_thenable(value):
            return value
        else:
            return cls(lambda ok, error: ok(value), _name='RESOLVE')

    @classmethod
    def reject(cls, reason):
        """Create a Promise rejected for the reason specified.

        Args:
            reason: Exception set to the Promise
        Returns:
            Promise: new Promise already rejected.
        """
        return cls(lambda ok, error: error(reason), _name='REJECT')

    @staticmethod
    def _exec_callback(callback, value, is_errback=False):
        try:
            callback(value)
        except:
            if is_errback:
                _logger.exception("Promise errback raise an exception!")
            else:
                _logger.exception("Promise callback raise an exception!")

    def _add_callback(self, callback):
        execute_now = False
        result = None

        with self._condition:
            if self._state == self.PENDING:
                self._callbacks.append(callback)
            else:
                if self._state == self.FULFILLED:
                    execute_now = True
                    result = self._result

        if execute_now:
            self._exec_callback(callback, result)

    def _add_errback(self, errback):
        execute_now = False
        error = None

        with self._condition:
            if self._state == self.PENDING:
                self._errbacks.append(errback)
            else:
                if self._state == self.REJECTED:
                    execute_now = True
                    error = self._error

        if execute_now:
            self._exec_callback(errback, error, is_errback=True)
