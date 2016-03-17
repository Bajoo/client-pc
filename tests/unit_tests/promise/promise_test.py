# -*- coding: utf-8 -*-

import logging
import pytest
import random
import sys
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


class TestThenMethod(object):

    def setup_method(self, method):
        logger = logging.getLogger()
        for h in list(logger.handlers):
            logger.removeHandler(h)

    def test_then_sync_call(self):
        """Test to chain a callback using then() on an fulfilled Promise."""

        def _callback(arg):
            assert arg is 23
            return arg * 2

        p = Promise(lambda ok, error: ok(23))
        p2 = p.then(_callback)
        assert p2.result(0.01) is 46
        assert p.result(0.01) is 23

    def test_then_async_call(self):
        """Chain a callback using then() on an not-yet fulfilled Promise."""

        _fulfill = []

        def _init(ok, error):
            _fulfill.append(ok)

        def _callback(arg):
            assert arg is 23
            return arg * 2

        p = Promise(_init)
        p2 = p.then(_callback)
        _fulfill[0](23)  # fulfill the Promise now.
        assert p2.result(0.01) is 46
        assert p.result(0.01) is 23

    def test_then_on_failing_sync_promise(self):
        """Chain a callback using then() to a Promise raising an exception"""
        class Err(Exception):
            pass

        def _task(ok, error):
            raise Err()

        def _callback(__):
            assert not 'This should not be executed.'

        p = Promise(_task)
        p2 = p.then(_callback)
        with pytest.raises(Err):
            p2.result(0.01)

    def test_then_on_failing_async_promise(self):
        """Chain a callback using then() to a Promise who will be rejected."""
        class Err(Exception):
            pass

        _reject = []

        def _task(ok, error):
            _reject.append(error)

        def _callback(__):
            assert not 'This should not be executed.'

        p = Promise(_task)
        p2 = p.then(_callback)
        _reject[0](Err())  # fulfill the Promise now.
        with pytest.raises(Err):
            p2.result()

    def test_then_with_promise_factory(self):
        """Chain a Future factory, using then().

        a Promise factory is a function who returns a Promise.
        """

        def factory(value):
            x = Promise(lambda ok, error: ok(value * value))
            return x

        p = Promise(lambda ok, error: ok(6))
        p2 = p.then(factory)
        assert p2.result(0.01) is 36

    def test_then_with_error_callback_on_fulfilled_promise(self):
        """Chain a Promise with both success and error callbacks.
        Only the success callback should be called.
        """
        def on_success(value):
            return value * 3

        def on_error(err):
            raise Exception('This should never be called!')

        p = Promise(lambda ok, error: ok(654))
        p2 = p.then(on_success, on_error)
        assert p2.result(0.01) == 1962

    def test_then_with_error_callback_on_rejected_promise(self):
        """Chain a Promise with both success and error callbacks.

        Only the error callback should be called.
        The resulting Promise will (successfully) resolve with the value
        returned by the error callback.
        """
        class MyException(Exception):
            pass

        def task(ok, error):
            error(MyException())

        def on_success(value):
            raise Exception('This should never be called!')

        def on_error(err):
            assert type(err) is MyException
            return 38

        p = Promise(task)
        p2 = p.then(on_success, on_error)
        assert p2.result(0.01) is 38

    def test_then_with_error_callback_only_on_fulfilled_promise(self):
        """Chain a successful Promise with only the error callback."""
        def on_error(err):
            raise Exception('This should never be called!')

        p = Promise(lambda ok, error: ok(185))
        p2 = p.then(None, on_error)
        assert p2.result(0.01) is 185

    def test_then_with_error_callback_only_on_rejected_promise(self):
        """Chain a failing promise with only the error callback."""
        class MyException(Exception):
            pass

        def task(ok, error):
            raise MyException()

        def on_error(err):
            assert isinstance(err, MyException)
            return 8

        p = Promise(task)
        p2 = p.then(None, on_error)
        assert p2.result(0.01) is 8

    def test_resolve_value(self):
        """Wrap a value into a Promise using Promise.resolve()."""
        p = Promise.resolve('xyz')
        assert p.result(0.01) is 'xyz'

    def test_resolve_future(self):
        """Use Promise.resolve() on an object who is already a Promise."""

        p = Promise.resolve(Promise.resolve(33))
        assert p.result(0.01) == 33

    def test_promise_safe_guard(self, capsys):
        """Use the safeguard() on a failing promise.

        It ensures the error is logged in the stdout, with sufficient details.

        """
        class Err(Exception):
            pass

        logging.basicConfig(stream=sys.stdout)

        def in_promise(a, b):
            msg = 'ERROR'
            raise Err(msg)

        p = Promise(in_promise)

        def callback(value):
            assert value is 3

        p.then(callback)
        p.safeguard()

        out, err = capsys.readouterr()
        assert '[SAFEGUARD]' in out


class TestGroupPromiseMethods(object):
    """Test the method which manipulate group of promises."""

    def test_method_all_with_empty_set(self):
        p = Promise.all([])
        assert p.result(0.001) == []

    def test_method_all_with_one_promise(self):
        p1 = Promise.resolve('RESULT')
        p = Promise.all([p1])
        assert p.result(0.001) == ['RESULT']

    def test_method_all_with_one_rejected_promise(self):
        class MyException(Exception):
            pass

        p1 = Promise.reject(MyException())
        p = Promise.all([p1])

        with pytest.raises(MyException):
            p.result(0.001)

    def test_method_all_with_several_promises(self):
        promises = [Promise.resolve(1) for _ in range(0, 20)]

        p = Promise.all(promises)

        assert sum(p.result()) is 20

    def test_method_all_with_rejected_promise(self):
        class MyException(Exception):
            pass

        promises = [Promise.resolve(1) for _ in range(0, 5)]
        promises += [Promise.reject(MyException())]
        promises += [Promise.resolve(1) for _ in range(0, 5)]

        p = Promise.all(promises)
        with pytest.raises(MyException):
            p.result()

    def test_method_all_with_async_promises(self):
        promises = [Promise.resolve(1) for _ in range(0, 5)]

        _resolve_callback = []

        def _init(ok, _error):
            _resolve_callback.append(ok)

        promises.append(Promise(_init))

        p = Promise.all(promises)

        # The ALL promise is not yet resolved.
        with pytest.raises(TimeoutError):
            p.result(0)

        _resolve_callback[0]('OK')

        # Now, all sub-promises are resolved.
        assert len(p.result(0.001)) is 6

    def test_method_all_must_keep_order(self):
        promises = []
        _resolve_callback = []

        for i in range(0, 25):
            def _promise_init(ok, _error):
                # Will resolve with the increment value.
                local_i = i
                _resolve_callback.append(lambda: ok(local_i))

            promises.append(Promise(_promise_init))

        # promises are ordered.
        p = Promise.all(promises)

        # Resolves the promises in a random order
        random.shuffle(_resolve_callback)
        for callback in _resolve_callback:
            callback()

        assert p.result(0.001) == list(range(0, 25))

    def test_method_race_with_empty_set(self):
        with pytest.raises(ValueError):
            Promise.race([])

    def test_method_race_with_one_promise(self):
        p1 = Promise.resolve('RESULT')
        p = Promise.race([p1])
        assert p.result(0.001) == 'RESULT'

    def test_method_race_with_several_promises(self):
        _resolve_callback = []

        def _async_promise(ok, _error):
            _resolve_callback.append(ok)

        # Add non-resolving promises.
        promises = [Promise(lambda _ok, _err: None) for _ in range(0, 5)]

        promises.append(Promise(_async_promise))
        promises.append(Promise(_async_promise))

        # Add non-resolving promises.
        promises += [Promise(lambda _ok, _err: None) for _ in range(0, 5)]

        p = Promise.race(promises)

        with pytest.raises(TimeoutError):
            p.result(0)
        _resolve_callback[0]('RESULT')

        # p is resolved after the first Promise resolves.
        assert p.result(0.001) == 'RESULT'

        # subsequent Promises resolutions should have no effect.
        _resolve_callback[1]('RESULT2')
        assert p.result(0.001) == 'RESULT'

    def test_method_race_with_failing_promises(self):
        class MyException(Exception):
            pass

        _reject_promise = []

        def _failing_async_promise(_ok, error):
            _reject_promise.append(error)

        promises = [Promise(_failing_async_promise) for _ in range(0, 15)]

        p = Promise.race(promises)

        with pytest.raises(TimeoutError):
            p.result(0)

        random.shuffle(_reject_promise)
        reject = _reject_promise.pop(0)
        reject(MyException())
        assert isinstance(p.exception(0.001), MyException)

        # subsequent rejection are ignored
        for reject in _reject_promise:
            reject(ValueError())

        assert isinstance(p.exception(0.001), MyException)
