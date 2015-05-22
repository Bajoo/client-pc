# -*- coding: utf-8 -*-
"""Helpers to perform more high-level operations on Future instances."""

import concurrent.futures


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

    new_future = concurrent.futures.Future()

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
        last_future = then(then(future, second_action), third_action)
        print('Final result: %s' % last_future.result())

if __name__ == "__main__":
    main()
