# -*- coding: utf-8 -*-

import threading

from bajoo.generic_executor import GenericExecutor, SharedContext


class TestGenericExecutor(object):

    def test_workers_are_all_executed(self):
        results = [0]

        def _worker_fn(context):
            with context:
                results[0] += 1
                if results[0] is 5:
                    context.condition.notify()

        with GenericExecutor('test', 5, _worker_fn) as e:
            with e.context:
                e.context.condition.wait(0.01)
            assert results[0] is 5

    def test_shutdown(self):
        stopped = [0]

        def _worker(context):
            with context:
                while not context.stop_order:
                    context.condition.wait()
            stopped[0] += 1

        e = GenericExecutor('test', 6, _worker)

        e.start()
        e.stop()
        assert stopped[0] is 6

    def test_executor_can_be_restarted(self):
        nb_threads = threading.active_count()

        def _dummy_worker(context):
            with context:
                while not context.stop_order:
                    context.condition.wait()

        e = GenericExecutor('test', 6, _dummy_worker)

        # First start / stop
        with e:
            assert threading.active_count() is nb_threads + 6

        assert threading.active_count() is nb_threads

        # Second start / stop
        e.start()
        assert threading.active_count() is nb_threads + 6
        e.stop()
        assert threading.active_count() is nb_threads

    def test_worker_threads_have_a_custom_name(self):
        names = []

        def _worker_fn(context):
            with context:
                names.append(threading.current_thread().name)

        with GenericExecutor('test-name', 4, _worker_fn):
            pass

        assert len(names) is 4
        assert len(names) is len(set(names))  # assert all elements are unique
        for name in names:
            assert 'test-name' in name

    def test_executor_handle_crashes(self):
        nb_started = [0]
        crash_order = [False]

        def _worker(context):
            nb_started[0] += 1

            with context:
                context.condition.notify()  # notify has started
                while not context.stop_order:
                    if crash_order[0]:
                        crash_order[0] = False
                        raise Exception("Expected crash")
                    context.condition.wait()

        with GenericExecutor('test', 2, _worker) as e:
            with e.context:
                # send a crash order. The first thread to detect it will raise
                # an exception, and so restart.
                crash_order[0] = True
                e.context.condition.notify()
                e.context.condition.wait(0.01)  # wait for "start" notification

        assert nb_started[0] is 3

    def test_executor_with_custom_context(self):
        class CustomContext(SharedContext):
            def __init__(self):
                super(CustomContext, self).__init__()
                self.custom_attribute = 0

        def _worker(context):
            with context:
                context.custom_attribute += 1

        context = CustomContext()
        with GenericExecutor('test-name', 3, _worker, context) as e:
            assert e.context is context
        assert context.customcontext is 3
