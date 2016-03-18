# -*- coding: utf-8 -*-

import pytest

from bajoo.promise import Deferred, Promise, TimeoutError


class TestDeferred(object):

    def test_deferred_resolve_promise(self):
        df = Deferred()
        assert isinstance(df.promise, Promise)

        with pytest.raises(TimeoutError):
            df.promise.result(0.001)
        df.resolve('Value')
        assert df.promise.result(0.001) == 'Value'

    def test_deferred_reject_promise(self):
        class MyException(Exception):
            pass

        df = Deferred()
        with pytest.raises(TimeoutError):
            df.promise.result(0.001)
        df.reject(MyException())

        with pytest.raises(MyException):
            df.promise.result(0.001)
