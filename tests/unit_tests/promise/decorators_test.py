# -*- coding: utf-8 -*-

import pytest

from bajoo.promise import Promise, wrap_promise


class TestDecorator(object):

    def test_wrap_sync_function(self):
        @wrap_promise
        def f(x):
            return x * 3

        p = f(30)
        assert isinstance(p, Promise)
        assert p.result(0.001) == 90

    def test_wrap_function_returning_promise(self):
        @wrap_promise
        def f(x):
            return Promise.resolve(x + 10)

        p = f(30)
        assert isinstance(p, Promise)
        assert p.result(0.001) == 40

    def test_wrap_function_with_exception(self):
        class MyException(Exception):
            pass

        @wrap_promise
        def f(x):
            raise MyException()

        p = f(30)
        assert isinstance(p, Promise)
        with pytest.raises(MyException):
            assert p.result(0.001) == 40
