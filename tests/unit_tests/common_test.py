# -*- coding: utf8 -*-

from concurrent.futures import CancelledError, ThreadPoolExecutor
from threading import Lock
import pytest

from bajoo.common.future import Future, patch, patch_dec, then, main


class TestFuture(object):
    """Test of the bajoo.common.future module"""

    def test_main(self):
        """Try the small main() presentation function of the module.

        This test just ensures that the main() don't throaw an exception.
        The execution may or may not be correct.
        """
        main()

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

    def test_then_on_failing_future(self):
        """Chain a callback using then() to a future raising an exception"""
        def _task():
            raise NotImplementedError

        def _callback(__):
            assert not 'This should not be executed.'

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_task)
            second_future = then(future, _callback)

        with pytest.raises(NotImplementedError):
            second_future.result()

    def test_then_on_cancelled_future(self):
        """Using then() ,on a cancelled future will raises an exception."""
        wait_lock = Lock()

        # This task will block until the lock is available.
        def _task_wait_lock(lock):
            lock.acquire()
            lock.release()

        def _callback(arg):
            raise Exception('This should never be called.')

        wait_lock.acquire()
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_task_wait_lock, wait_lock)

            future = executor.submit(lambda: 23)
            assert future.cancel() is True
            wait_lock.release()
            with pytest.raises(CancelledError):
                then(future, _callback)

    def test_patched_future(self):
        """Patch the future and chain the future with a callback."""

        def _callback(arg):
            assert arg is 82
            return arg // 2

        with ThreadPoolExecutor(max_workers=1) as executor:
            future_first_step = patch(executor.submit(lambda: 82))
            future_second_step = future_first_step.then(_callback)

            assert future_second_step.result(1) is 41

    def test_patch_decorator(self):
        """Patch a function who returns a future and test the result."""

        @patch_dec
        def async_method():
            with ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(lambda: 33)

        def _callback(arg):
            assert arg is 33
            return arg * 3

        future_first_step = async_method()
        future_second_step = future_first_step.then(_callback)
        assert future_second_step.result(1) is 99

    def test_resolve_value(self):
        """Wrap a value into a future using Future.resolve()."""
        future = Future.resolve('xyz')
        assert not future.cancelled()
        assert not future.running()
        assert future.done()
        assert future.result() is 'xyz'

    def test_resolve_future(self):
        """Use Future.resolve() on an object who is already a future."""

        with ThreadPoolExecutor(max_workers=1) as executor:
            f = executor.submit(lambda: 33)
            future = Future.resolve(f)
            assert future.result(1) is 33
