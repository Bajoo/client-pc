# -*- coding: utf-8 -*-

from bajoo.promise import ThreadPoolExecutor


class TestThreadPoolExecutor(object):

    def test_small_task(self):
        executor = ThreadPoolExecutor(1)

        def task(arg):
            return 'OK %s' % arg

        f = executor.submit(task, 'ARG')
        assert f.result(0.01) == 'OK ARG'

    def test_task_failure(self):
        class MyException(Exception):
            pass

        executor = ThreadPoolExecutor(1)

        def task(arg):
            raise MyException

        f = executor.submit(task, 'ARG')
        assert isinstance(f.exception(0.01), MyException)
