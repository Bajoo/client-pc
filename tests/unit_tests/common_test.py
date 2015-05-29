# -*- coding: utf8 -*-

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from bajoo.common.future import then


class TestFuture(object):
    """Test of the bajoo.common.future module"""

    def test_then_before_run(self):
        """Test to chain a callback using then() before start.

        The chain is created when the future hasn't started yet.
        """
        wait_lock = Lock()

        # This task will block until the lock is available.
        def _task_wait_lock(lock):
            lock.acquire()
            lock.release()

        def _callback(arg):
            assert arg is 23
            return arg * 2

        wait_lock.acquire()
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_task_wait_lock, wait_lock)

            future_first_step = executor.submit(lambda: 23)
            future_second_step = then(future_first_step, _callback)

            wait_lock.release()
            assert future_second_step.result(1) is 46

    def test_then_during_run(self):
        """Chain a callback using then() to a future currently running"""
        start_lock = Lock()
        end_lock = Lock()
        start_lock.acquire()
        end_lock.acquire()

        def _task():
            start_lock.release()  # this will "unlock" the main thread.
            # Now, wait until the main thread has set the callback.
            end_lock.acquire()
            return 44

        def _callback(arg):
            assert arg is 44
            return arg * 2

        with ThreadPoolExecutor(max_workers=1) as executor:
            future_first_step = executor.submit(_task)
            start_lock.acquire()  # wait the _task thread to be started.
            future_second_step = then(future_first_step, _callback)
            end_lock.release()  # tell the _task thread to terminate.

            assert future_second_step.result(1) is 88

    def test_then_after_run(self):
        """Chain a callback using then() to a future already terminated."""
        def _callback(arg):
            assert arg is 56
            return arg * 2

        with ThreadPoolExecutor(max_workers=1) as executor:
            future_first_step = executor.submit(lambda: 56)
            future_first_step.result()
            future_second_step = then(future_first_step, _callback)

            assert future_second_step.result(1) is 112
