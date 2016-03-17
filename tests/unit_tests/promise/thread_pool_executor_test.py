# -*- coding: utf-8 -*-

from bajoo.promise import ThreadPoolExecutor


class TestThreadPoolExecutor(object):

    def test_small_task(self):
        executor = ThreadPoolExecutor(1)

        def task(arg):
            return 'OK %s' % arg

        f = executor.submit(task, 'ARG')
        assert f.result(0.01) == 'OK ARG'
