# -*- coding: utf-8 -*-
"""Helpers to perform more high-level operations on Future instances.

It also provides a new class Future who extends concurrent.futures with all
the helpers as class methods.

For functions who returns directly a future, the function ``patch()`` can add
the helpers as class methods of a Future instances. ``patch_dec()`` is the
decorator version.
"""

import concurrent.futures
from functools import partial
import logging
from multiprocessing import Lock as ProcessLock
import sys
from threading import Lock as ThreadLock
import traceback
import types

_logger = logging.getLogger(__name__)


def then(original_future, on_success=None, on_error=None, no_arg=False):
    """Chain a callback to a Future instance.

    Execute the callback functions right after the future has been resolved.
    The final result will be returned as a Future (and so allowing to chain
    many operations).
    If the original future raises an exception and on_error is set, on_error()
    will be called. The value returned b on_error() will be the new result.

    If the original future is raises an exception and there is no on_error
    callback, then the new future (resulting of this call) will do the same.


    If the first future is cancelled, all chained futures will also be
    cancelled.
    Note that the inverse is not true: cancelling the new future will only
    prevent the callback from being executed, and not the original action.

    If a callback function returns another Future, the result of this generated
    future will be used. It allows to pass Future factory, and so chain futures
    together.

    If an exception is raised, the original stack is stored, as an str into
    error._origin_stack.

    Args:
        original_future: future who will be chained.
        on_success (callable, optional): This callback will receive the result
            of the original future as argument.
        on_on_error (callable, optional): This callback will receive the
            exception raised by the original future as argument.
        no_arg (boolean, optional): If True, the success callback is called
            without argument.
    Returns:
        Future<?>: a new future who represents the value returned by the
            callbacks.
    Raises:
        CancelledError: if the original future is already cancelled.
    """
    if original_future.cancelled():
        raise concurrent.futures.CancelledError

    new_future = Future()

    def _callback(self):
        if self.cancelled():
            new_future.cancel()
            return new_future.set_running_or_notify_cancel()

        new_future.set_running_or_notify_cancel()

        try:
            result = self.result()
            if not on_success:
                new_future.set_result(None if no_arg else result)
                return
            callback = on_success
            is_error = False
        except Exception as e:  # initial future has failed.
            if not on_error:
                new_future.set_exception(e)
                return
            result = e
            callback = on_error
            is_error = True

        try:
            if no_arg and is_error:
                new_result = callback()
            else:
                new_result = callback(result)
            if isinstance(new_result, concurrent.futures.Future):
                new_result.then(new_future.set_result,
                                new_future.set_exception)
            else:
                new_future.set_result(new_result)
        except Exception as e:
            exc_info = sys.exc_info()
            e._origin_stack = ''.join(traceback.format_exception(
                exc_info[0], exc_info[1], exc_info[2]))
            new_future.set_exception(e)

    original_future.add_done_callback(_callback)

    return new_future


class Future(concurrent.futures.Future):
    """Extended future, containing helpers as class methods."""

    @staticmethod
    def resolve(value):
        """Create a future who resolves the selected value.

        Args:
            value: result of the future. If it's a future, it's returned as is.
        Returns:
            Future: new Future already terminated, containing the value passed
                in parameter.
        """
        if isinstance(value, concurrent.futures.Future):
            return value

        future = Future()
        future.set_running_or_notify_cancel()
        future.set_result(value)
        return future

    @staticmethod
    def reject(value):
        """Create a future who contains an exception.

        Args:
            value: Exception set to the future
        Returns:
            Future: new Future already terminated, containing the exception.
        """
        future = Future()
        future.set_running_or_notify_cancel()
        future.set_exception(value)
        return future

    def then(self, on_success=None, on_error=None, no_arg=False):
        return then(self, on_success, on_error, no_arg=no_arg)


def resolve_dec(f):
    """Decorator who converts the result in a Future object.

    If the function decorated returns a Future, it's transmitted as is.
    Else, a new Future is created with the returned value as result.
    """
    def wrapper(*args, **kwargs):
        try:
            return Future.resolve(f(*args, **kwargs))
        except Exception as error:
            return Future.reject(error)

    return wrapper


def patch(future):
    """Add helpers function as new class methods of a Future instance.

    Args:
        Future: future to patch
    Returns:
        Future: the patched future.
    """
    future.then = types.MethodType(then, future)
    return future


def patch_dec(f):
    """Patch Future instance returned to add helpers class methods.

    Decorator of method who returns a Future object. The returning object will
    be modified to accept the helpers as new class methods.

    If the function doesn't returns a future, the result is not modified.

    Args:
        f (callable): function susceptible to returns Future instances.
    """
    def wrapper(*args, **kwargs):
        result = f(*args, **kwargs)
        if isinstance(result, concurrent.futures.Future):
            return patch(result)
        return result

    return wrapper


def wait_one(futures, cancel_others=False):
    """Wait until one of the futures resolves.

    When one of the tasks is over, the future returns, with the same value.
    All others tasks results will be ignored.

    This method is thread-safe and multiprocess-safe.

    Args:
        futures (list of Future): list of tasks to wait.
        cancel_others (boolean ,optional): if set, try to cancel others tasks
            when the first one is done.
    Returns:
        Future<?>: result of the first finished task.
    """
    tlock, plock = ThreadLock(), ProcessLock()
    resulting_future = Future()

    def _done_callback(value):
        with tlock, plock:
            if resulting_future.done():
                return  # Another future has already finished.
            if cancel_others:
                for f in futures:
                    f.cancel()
            resulting_future.set_running_or_notify_cancel()
            resulting_future.set_result(value)

    def _fail_callback(exception):
        with tlock, plock:
            if resulting_future.done():
                return  # Another future has already finished.
            resulting_future.set_running_or_notify_cancel()
            resulting_future.set_exception(exception)
            if cancel_others:
                for f in futures:
                    f.cancel()

    for f in futures:
        f.then(_done_callback, _fail_callback)
    return resulting_future


def wait_all(futures):
    """Create a future who wait that all futures in the list are resolved.

    returns:
        Future<list>: list of all results from each future.
    """
    tlock, plock = ThreadLock(), ProcessLock()
    resulting_future = Future()

    _remaining_tasks = [len(futures)]
    results = [None] * len(futures)

    if _remaining_tasks[0] == 0:
        return Future.resolve([])

    def _done_callback(index, value):
        with tlock, plock:
            if _remaining_tasks[0] <= 0:
                return
            _remaining_tasks[0] -= 1
            results[index] = value
            if _remaining_tasks[0] == 0:
                resulting_future.set_running_or_notify_cancel()
                resulting_future.set_result(results)

    def _fail_callback(exception):
        with tlock, plock:
            if _remaining_tasks[0] <= 0:
                return
            resulting_future.set_running_or_notify_cancel()
            resulting_future.set_exception(exception)
            _remaining_tasks[0] = -1

    for index, f in enumerate(futures):
        if f is None:
            _logger.warning('wait_all() have received a None value in the list'
                            ' of future to wait. That should not happen!')
        else:
            then(f, partial(_done_callback, index), _fail_callback)

    return resulting_future


def resolve_rec(result):
    """Recursively resolve the future if it returns another Future.

    In same case, an asynchronous action must be done in many steps, not known
    at start. resolve_rec() allow a Future to resolve itself as another Future
    object (the next step), and so recursively.

    Returns:
        Future<?>: Future guaranteed to resolve a non-future result.
    """
    if isinstance(result, concurrent.futures.Future):
        return then(result, resolve_rec)
    else:
        return Future.resolve(result)


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:

        def first_action():
            print('First action.')
            return 3

        def second_action(arg):
            print('Second action: received %s from the first one.' % arg)
            print('Will return the square of the value.')
            return arg * arg

        def third_action(arg):
            print('Last chained action. Received %s' % arg)
            return arg

        future = executor.submit(first_action)
        patch(future)
        last_future = future.then(second_action).then(third_action)
        print('Final result: %s' % last_future.result())

if __name__ == "__main__":
    main()
