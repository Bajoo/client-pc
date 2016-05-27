# -*- coding: utf-8 -*-

from contextlib import contextmanager
import pytest
import threading
from time import sleep
from bajoo.common.periodic_task import PeriodicTask

import logging

logging.basicConfig()


def slow_test_dec():
    """Decorator for slow test methods."""
    slow_enabled = bool(pytest.config.getvalue('slowtest'))
    return pytest.mark.skipif(not slow_enabled, reason='slow test')


class TestPeriodicTask(object):

    def _collect_info_task(self, pt, *args, **kwargs):
        """Task for a PeriodicTask which collects info."""
        pt.context['args'] = args
        pt.context['kwargs'] = kwargs
        pt.context['count'] = pt.context.get('count', 0) + 1

    @contextmanager
    def run_periodic_task_context(self, pt):
        """Properly start and stop the PeriodicTask."""
        pt.start()
        try:
            yield pt
        finally:
            pt.stop()

    def test_constructor_args_and_attributes_matches(self):
        pt = PeriodicTask('Test', 23, lambda _: None, 1, 2, 3, foo='bar')
        assert pt.delay is 23
        assert pt.args == (1, 2, 3)
        assert pt.kwargs == {'foo': 'bar'}

    def test_start_periodic_task_should_be_executed_immediately(self):
        pt = PeriodicTask('Test', 23, self._collect_info_task)
        with self.run_periodic_task_context(pt):
            sleep(0.01)
            assert pt.context['count'] == 1

    def test_task_receive_pt_as_first_arg(self):
        context = {}

        def task(pt):
            context['pt'] = pt

        pt = PeriodicTask('Test', 23, task)
        with self.run_periodic_task_context(pt):
            sleep(0.01)
            assert context['pt'] == pt

    def test_shared_context(self):
        def task(pt):
            # assert raised inside a task are ignored by pytest, but it'll
            # prevent the 2nd value to be set, so the test will fail anyway.
            assert pt.context['test #1'] == 9
            pt.context['test #2'] = 23

        pt = PeriodicTask('Test', 23, task)
        pt.context['test #1'] = 9
        with self.run_periodic_task_context(pt):
            sleep(0.01)
            assert pt.context['test #2'] == 23

    def test_start_periodic_task_with_args(self):
        pt = PeriodicTask('Test', 23, self._collect_info_task, 'arg1', 'arg2',
                          kwargs1='kwargs1')

        with self.run_periodic_task_context(pt):
            sleep(0.01)
            assert pt.context['args'] == ('arg1', 'arg2')
            assert pt.context['kwargs'] == {'kwargs1': 'kwargs1'}

    def test_thread_name_is_set(self):
        thread_name = 'My test task'

        def task(pt):
            pt.context['thread_name'] = threading.current_thread().name

        pt = PeriodicTask(thread_name, 23, task)

        with self.run_periodic_task_context(pt):
            sleep(0.01)
            assert pt.context['thread_name'] == thread_name

    @slow_test_dec()
    def test_periodic_task_is_executed_many_times(self):
        pt = PeriodicTask('Test', 0.5, self._collect_info_task)

        with self.run_periodic_task_context(pt):
            sleep(1.1)
            assert pt.context['count'] == 3

    @slow_test_dec()
    def test_periodic_task_can_be_stopped(self):
        pt = PeriodicTask('Test', 0.5, self._collect_info_task)

        pt.start()
        sleep(0.01)
        pt.stop()
        sleep(1)
        assert pt.context['count'] == 1

    @slow_test_dec()
    def test_task_can_stop_itself(self):
        def auto_stop_task(pt):
            pt.stop()
            pt.context['count'] += 1

        pt = PeriodicTask('Test', 0.5, auto_stop_task)
        pt.context['count'] = 0

        with self.run_periodic_task_context(pt):
            sleep(1)
            assert pt.context['count'] == 1

    def test_apply_now(self):
        def task(pt):
            pt.context['count'] += 1
            return pt.context['count']

        pt = PeriodicTask('test', 99, task)
        pt.context['count'] = 0

        with self.run_periodic_task_context(pt):
            sleep(0.01)
            promise = pt.apply_now()
            assert promise.result(0.01) is 2

    def test_apply_now_when_task_is_running(self):
        def task(pt):
            pt.context['count'] += 1
            if pt.context['count'] == 1:
                # 2nd execution will start just after this one.
                pt.context['promise'] = pt.apply_now()

            return pt.context['count']

        pt = PeriodicTask('test', 99, task)
        pt.context['count'] = 0

        with self.run_periodic_task_context(pt):
            sleep(0.1)
            assert pt.context['count'] == 2
            assert pt.context['promise'].result(0.01) is 2

    def test_apply_now_with_failure(self):
        class MyException(Exception):
            pass

        def task(pt):
            if pt.context['apply_now_mode']:
                raise MyException()

        pt = PeriodicTask('test', 99, task)
        pt.context['apply_now_mode'] = False
        with self.run_periodic_task_context(pt):
            sleep(0.01)
            pt.context['apply_now_mode'] = True
            promise = pt.apply_now()
            assert isinstance(promise.exception(), MyException)

    @slow_test_dec()
    def test_delay_can_be_changed(self):
        pt = PeriodicTask('Test', 0.5, self._collect_info_task)

        with self.run_periodic_task_context(pt):
            sleep(1.01)
            assert pt.context['count'] == 3
            pt.context['count'] = 0
            pt.delay = 0.1
            # Next execution is scheduled at 1.5s from pt.start() (or 500ms
            # from now). After that, the new delay will be used, so each 100ms
            # for 500ms.
            sleep(1)
            assert pt.context['count'] == 6
