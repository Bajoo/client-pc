# -*- coding: utf-8 -*-
"""Helpers to perform more high-level operations on Future instances.

It also provides a new class Future who extends concurrent.futures with all
the helpers as class methods.

For functions who returns directly a future, the function ``patch()`` can add
the helpers as class methods of a Future instances. ``patch_dec()`` is the
decorator version.
"""

import concurrent.futures
import types


def then(original_future, callback):
    """Chain a callback to a Future instance.

    Execute the callback function right after the future has been resolved.
    The final result will be returned as a Future (and so allowing to chain
    many operations).

    If the original future is cancelled or raises an exception, then the new
    future (resulting of this call) will do the same.

    If the first future is cancelled, all chained futures will also be
    cancelled.
    Note that the inverse is not true: cancelling the new future will only
    prevent the callback from being executed, and not the original action.

    Args:
        original_future: future who will be chained.
        callback (callable): This callback will receive the result of the
            original future as argument.
    Returns:
        Future<?>: a new future who represents the value returned by the
            callback.
    Raises:
        CancelledError: if the original future is already cancelled.
    """
    if original_future.cancelled():
        raise concurrent.futures.CancelledError

    new_future = Future()

    def _callback(self):
        if not self.cancelled():
            new_future.set_running_or_notify_cancel()
            try:
                new_result = callback(self.result())
                new_future.set_result(new_result)
            except Exception as e:
                new_future.set_exception(e)
        else:
            new_future.cancel()
            new_future.set_running_or_notify_cancel()

    original_future.add_done_callback(_callback)

    return new_future


class Future(concurrent.futures.Future):
    """Extended future, containing helpers as class methods."""

    def then(self, callback):
        return then(self, callback)


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
