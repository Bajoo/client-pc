# -*- coding:utf-8 -*-

import threading
import pytest

from bajoo.filesync import task_consumer
from bajoo.promise import Promise


class TestTaskConsumer(object):

    def _make_external_promise(self):
        """Helper used to make stub Promise.

        Returns:
            Promise, resolve, reject: the promise and its callbacks.
        """
        callbacks = []

        def executor(resolve, reject):
            callbacks.append(resolve)
            callbacks.append(reject)
        return Promise(executor), callbacks[0], callbacks[1]

    def test_add_empty_task(self):
        """Add a task who is an almost empty generator."""

        with task_consumer.Context():
            task_executed = []

            def task():
                task_executed.append(True)
                yield

            promise = task_consumer.add_task(task)
            promise.result(0.01)
            assert task_executed

    def test_add_task_returning_value(self):
        """Add a simple task who must return a value."""
        with task_consumer.Context():

            def task():
                yield 56

            promise = task_consumer.add_task(task)
            assert promise.result(0.01) is 56

    def test_add_task_multistep(self):
        """Add a task who has to wait other external tasks (promise)."""
        p1, resolve, _ = self._make_external_promise()
        p2, resolve2, _ = self._make_external_promise()

        def task():
            value = yield p1
            assert value is 44

            value2 = yield p2
            yield value2 * 2

        with task_consumer.Context():
            p_task = task_consumer.add_task(task)
            resolve(44)
            resolve2(26)
            assert p_task.result(0.01) is 52

    def test_all_step_use_dedicated_thread(self):
        """Ensures the code in a task is always executed in a filesync thread.

        The generator code is always executed in a thread belonging to the
        filesync threads.
        """
        main_thread = threading.current_thread().ident
        p1, resolve, _ = self._make_external_promise()
        p2, resolve2, _ = self._make_external_promise()

        def task():
            assert threading.current_thread().ident is not main_thread
            yield p1
            assert threading.current_thread().ident is not main_thread
            yield p2
            assert threading.current_thread().ident is not main_thread
            yield Promise.resolve(None)
            assert threading.current_thread().ident is not main_thread

        with task_consumer.Context():
            p_task = task_consumer.add_task(task)
            resolve(None)
            resolve2(None)
            p_task.result(0.01)

    def test_add_task_waiting_rejected_promise(self):
        """Add a task who should fail due to a rejected promise."""
        class Err(Exception):
            pass

        def task():
            yield Promise.resolve('OK')
            yield Promise.reject(Err())

        with task_consumer.Context():
            p = task_consumer.add_task(task)
            with pytest.raises(Err):
                p.result(0.01)

    def test_add_task_catching_rejected_promise(self):
        """Add a task who will catch a rejected promise."""
        class Err(Exception):
            pass

        def task():
            yield Promise.resolve('OK')
            with pytest.raises(Err):
                yield Promise.reject(Err())
            yield 'OK'

        with task_consumer.Context():
            p = task_consumer.add_task(task)
            assert p.result(0.01) == 'OK'

    def test_add_failing_task(self):
        """Add a task who will raises an Exception."""
        class Err(Exception):
            pass

        def task():
            yield Promise.resolve(True)
            raise Err()

        with task_consumer.Context():
            p = task_consumer.add_task(task)

            with pytest.raises(Err):
                p.result(0.1)

    def test_add_many_tasks(self):
        """Add 100 new tasks and wait them all."""
        promises = []

        def task():
            yield Promise.resolve(1)
            yield Promise.resolve(2)
            yield Promise.resolve(3)
            yield 1
        with task_consumer.Context():
            for i in range(40):
                promises.append(task_consumer.add_task(task))

            result = Promise.all(promises).result(0.1)
            print(result)

            assert sum(result) is 40

    def test_add_concurrent_tasks(self):
        """Add three tasks who are required to run at the same time.

        The task A will wait the Task B, then B will wait A.

        This test "force" the tasks to be executed in a non-linear order.

        """
        p1_a, r1_a, _ = self._make_external_promise()
        p1_b, r1_b, _ = self._make_external_promise()
        p1_c, r1_c, _ = self._make_external_promise()
        p2_a, r2_a, _ = self._make_external_promise()
        p2_b, r2_b, _ = self._make_external_promise()
        p2_c, r2_c, _ = self._make_external_promise()

        def task_A():
            r1_a(None)
            yield p1_b
            r2_a(None)
            yield p2_c
            yield 'A'

        def task_B():
            r1_b(None)
            yield p1_c
            r2_b(None)
            yield p2_a
            yield 'B'

        def task_C():
            r1_c(None)
            yield p1_a
            r2_c(None)
            yield p2_b
            yield 'C'

        with task_consumer.Context():
            results = Promise.all([
                task_consumer.add_task(task_A),
                task_consumer.add_task(task_B),
                task_consumer.add_task(task_C)
            ]).result(0.01)
            assert results == list('ABC')

    def test_ensure_task_generator_are_closed(self):
        """Ensure the task generators are properly closed after use.

        If a generator has yielded the final result, and the caller don't want
        to iter until the end, the caller must close the generator.
        Closing the generator will raise an exception GeneratorExit, and so
        allow the generator to clean resources.
        Without the close, resources locked by `with` will not be released.
        """
        is_generator_closed = []

        def task():
            try:
                yield 'RESULT'
            except GeneratorExit:
                is_generator_closed.append(True)

        with task_consumer.Context():
            p = task_consumer.add_task(task)
            assert p.result(0.01) == 'RESULT'
            assert is_generator_closed
