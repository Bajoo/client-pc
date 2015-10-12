# -*- coding: utf8 -*-

import pytest
from threading import Timer
from bajoo.promise import Promise, TimeoutError


class TestPromise(object):

    def test_synchronous_call(self):
        """Make a Promise fulfilled by a synchronous function and get result"""

        def executor(on_fulfilled, on_rejected):
            on_fulfilled(3)

        p = Promise(executor)

        assert p.result() is 3

    def test_synchronous_call_failing(self):
        """Make a Promise rejected by a synchronous executor and get result."""

        class Err(Exception):
            pass

        def executor(on_fulfilled, on_rejected):
            on_rejected(Err())

        p = Promise(executor)
        with pytest.raises(Err):
            p.result()

    def test_executor_raising_error(self):
        """Make a Promise with an executor raising an error and get result."""
        class Err(Exception):
            pass

        def executor(on_fulfilled, on_rejected):
            raise Err()

        p = Promise(executor)
        with pytest.raises(Err):
            p.result()

    def test_get_error_fulfilled_promise(self):
        """Get the exception of a fulfilled Promise."""
        def executor(on_fulfilled, on_rejected):
            on_fulfilled('result value')

        p = Promise(executor)
        assert p.exception() is None

    def test_get_error_rejected_promise(self):
        """Get the exception of a rejected Promise."""
        class Err(Exception):
            pass

        def executor(on_fulfilled, on_rejected):
            on_rejected(Err())

        p = Promise(executor)

        err = p.exception()
        assert isinstance(err, Err)

    def test_asynchronous_call(self):
        """Make a Promise fulfilled after the call to result()."""

        def executor(on_fulfilled, on_rejected):
            Timer(0.001, on_fulfilled, args=['OK']).start()

        p = Promise(executor)
        assert p.result() == 'OK'

    def test_get_result_timeout(self):
        """Try to get the result with a timeout while the Promise is pending.
        """
        def executor(on_fulfilled, on_rejected):
            pass

        p = Promise(executor)

        with pytest.raises(TimeoutError):
            p.result(0)

    def test_async_failing_call(self):
        """Try to get the result of a failing Promise while it's pending."""
        class Err(Exception):
            pass

        def executor(on_fulfilled, on_rejected):
            Timer(0.001, on_rejected, args=[Err()]).start()

        p = Promise(executor)
        with pytest.raises(Err):
            p.result()

    def test_get_error_async_fulfilled_promise(self):
        """Get the exception of a Promise who will be fulfilled."""
        def executor(on_fulfilled, on_rejected):
            Timer(0.001, on_fulfilled, args=[1]).start()

        p = Promise(executor)
        assert p.exception() is None

    def test_get_error_async_rejected_promise(self):
        """Get the exception of a Promise soon to be rejected."""
        class Err(Exception):
            pass

        def executor(on_fulfilled, on_rejected):
            Timer(0.001, on_rejected, args=[Err()]).start()

        p = Promise(executor)
        assert isinstance(p.exception(), Err)
