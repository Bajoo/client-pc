# -*- coding: utf-8 -*-
"""Helpers to perform more high-level operations on Future instances.

It also provides a new class Future who extends concurrent.futures with all
the helpers as class methods.

For functions who returns directly a future, the function ``patch()`` can add
the helpers as class methods of a Future instances. ``patch_dec()`` is the
decorator version.
"""

import concurrent.futures
import logging
import sys
import traceback
from ..promise import is_thenable

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
            if is_thenable(new_result):
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

    def then(self, on_success=None, on_error=None, no_arg=False):
        return then(self, on_success, on_error, no_arg=no_arg)


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
        last_future = future.then(second_action).then(third_action)
        print('Final result: %s' % last_future.result())

if __name__ == "__main__":
    main()
