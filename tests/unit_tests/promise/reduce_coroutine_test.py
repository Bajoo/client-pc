# -*- coding: utf-8 -*-

import pytest

from bajoo import promise


class TestReduceCoroutine(object):

    def test_reduce_two_promises_coroutine(self):
        """Use @reduce_coroutine on a generator of two fulfilled promises.

        The most common Promise-generator case: a generator who yield two
        promises. the decorated coroutine must return a Promise who resolves
        when the generator is over.

        The last promise yielded contains the "result" value.
        """

        @promise.reduce_coroutine()
        def generator():
            first_value = yield promise.Promise.resolve(1)
            assert first_value
            yield promise.Promise.resolve(2)

        p = generator()
        assert isinstance(p, promise.Promise)
        assert p.result() is 2

    def test_reduce_direct_value_coroutine(self):
        """Use @reduce_coroutine on a generator yielding non-future result.

        The last value yielded by the generator is the "return" value. In this
        scenario, it's yielded without being wrapped in a Promise.
        """

        @promise.reduce_coroutine()
        def generator():
            first_value = yield promise.Promise.resolve(1)
            assert first_value
            second_value = yield promise.Promise.resolve(2)
            assert second_value is 2
            yield 3

        p = generator()
        assert isinstance(p, promise.Promise)
        assert p.result() is 3

    def test_reduce_coroutine_with_failed_promise(self):
        """Use @reduce_coroutine on a generator who yield rejected Promise

        If not caught (like in this case), the error is transmitted to the
        Promise p.
        """
        class Err(Exception):
            pass

        @promise.reduce_coroutine()
        def generator():
            first_value = yield promise.Promise.resolve(1)
            assert first_value
            yield promise.Promise.reject(Err())

        p = generator()
        assert isinstance(p, promise.Promise)
        err = p.exception(0.01)
        assert isinstance(err, Err)

    def test_reduce_coroutine_raising_exception(self):
        """Use @reduce_coroutine on a generator who raise an Exception."""
        class Err(Exception):
            pass

        @promise.reduce_coroutine()
        def generator():
            first_value = yield promise.Promise.resolve(1)
            assert first_value
            raise Err()

        p = generator()
        assert isinstance(p, promise.Promise)
        err = p.exception(0.01)
        assert isinstance(err, Err)

    def test_reduce_one_step_coroutine(self):
        """Use @reduce_coroutine on a generator who yield only once."""
        @promise.reduce_coroutine()
        def generator():
            yield 'direct_result'

        p = generator()
        assert p.result() == 'direct_result'

    def test_reduce_coroutine_raising_exception_at_initialization(self):
        """Use @reduce_coroutine on a generator raising error before any yield.

        A typical example is the coroutine raising due to missing call
        preconditions.
        """
        class Err(Exception):
            pass

        @promise.reduce_coroutine()
        def generator():
            raise Err()
            yield None

        p = generator()
        err = p.exception(0.01)
        assert isinstance(err, Err)

    def test_reduce_coroutine_catching_exception(self):
        """Use a generator who catch exceptions from Future.

        The coroutine uses the classical try/except block on yield
        instruction over a Promise.
        """
        class Err(Exception):
            pass

        @promise.reduce_coroutine()
        def generator():
            try:
                yield promise.Promise.reject(Err())
            except Err:
                yield 'fixed_result'
            yield 'never_yielded'

        p = generator()
        assert p.result(0.01) == 'fixed_result'

    def test_reduce_coroutine_close_generator(self):
        """Ensure the generator is properly closed when it returns a value.

        If a generator has yielded the final result, and the caller don't want
        to iter until the end, the caller must close the generator.
        Closing the generator will raise an exception GeneratorExit, and so
        allow the generator to clean resources.
        Without the close, resources locked by `with` will not be released.
        """
        is_generator_closed = []

        @promise.reduce_coroutine()
        def generator():
            try:
                yield 'RESULT'
            except GeneratorExit:
                is_generator_closed.append(True)

        p = generator()
        assert p.result(0.01) == 'RESULT'
        assert is_generator_closed

    def test_coroutine_empty_coroutine(self):
        """Use a coroutine who never yield (it returns directly)."""

        @promise.reduce_coroutine()
        def generator():
            return
            yield

        p = generator()
        assert p.result(0.01) is None

    @pytest.fixture
    def replace_safeguard(self, request):
        safeguard = promise.Promise.safeguard
        context = {'flag': False}

        def raise_flag(*args):
            context['flag'] = True
        promise.Promise.safeguard = raise_flag

        def _reset_safeguard():
            promise.Promise.safeguard = safeguard
        request.addfinalizer(_reset_safeguard)
        return context

    def test_use_safeguard(self, replace_safeguard):
        class Err(Exception):
            pass

        @promise.reduce_coroutine(safeguard=True)
        def generator():
            raise Err()
            yield None

        p = generator()
        assert isinstance(p.exception(0.001), Err)
        assert replace_safeguard['flag']
