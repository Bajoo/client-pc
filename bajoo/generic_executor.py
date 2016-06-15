# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor
import functools
import logging
import threading

_logger = logging.getLogger(__name__)


class SharedContext(object):
    """Thread-safe context shared between all workers of an executor.

    The context contains an instance of `threading.Condition`. This instance
    must be used to ensure thread-safe access to context elements, such as the
    stop order. Also, it can be called to wake up workers.

    The context contains a boolean value `stop_order`. When True, all workers
    should returns as soon as possible. When the stop order is triggered, all
    threads will be notified using the condition.

    Instances of SharedContext are context managers:
    `with context:` is a sugar syntax shortcut for `with context.condition`.

    The minimal worker function is like that:

    ```
    def worker(context):
        with context:
            while not context.stop_order:
                # ... make operations ...
                context.wait()
    ```

    Attributes:
        condition (Condition)
        stop_order (boolean): if True, the executor is in shutdown phase. All
            workers should stop immediately.
    """

    def __init__(self):
        self.condition = threading.Condition()
        self.stop_order = False

    def __enter__(self):
        self.condition.__enter__()
        return self

    def __exit__(self, _type, _value, _tb):
        return self.condition.__exit__(_type, _value, _tb)


class GenericExecutor(object):
    """Generic class for executor using never-ending workers.

    This executor starts all the workers at start. When a worker stops, or
    raises an exception, it's restarted again.

    It's up to the workers to manages the item queue and the synchronization
    between them.

    Attributes:
        context (SharedContext): context for communication with workers.
    """

    def __init__(self, worker_name, max_workers, fn, shared_context=None):
        """
        Args:
            worker_name (str): name of the workers. eg: 'network'.
            max_workers (int): maximum number of running worker.
            fn (callable): the worker function. A context will be passed to
                them at call.
            shared_context (SharedContext, optional): context shared between
               all workers. By default, a generic SharedContext is used. This
               argument allow to use extended instances with custom attributes
               to shares between workers.
        """
        if shared_context is not None:
            self.context = shared_context
        else:
            self.context = SharedContext()
        self._worker_name = worker_name
        self._max_workers = max_workers
        self._last_worker_id = 0

        self._executor = None
        self._fn = fn

    def start(self):
        """Start all the workers."""
        self.context.stop_order = False

        _logger.debug('Start service "%s"', self._worker_name)
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        for i in range(self._max_workers):
            self._last_worker_id += 1
            f = self._executor.submit(self._run_worker, self._last_worker_id)
            done_handler = functools.partial(self._handle_worker_ending,
                                             self._last_worker_id)
            f.add_done_callback(done_handler)

    def stop(self):
        """Stop all the workers.

        Returns only when all the worker threads are joined.
        """
        _logger.debug('Stop service "%s"', self._worker_name)
        with self.context:
            self.context.stop_order = True
            self.context.condition.notify_all()
        if self._executor:
            self._executor.shutdown()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, _type, _value, _tb):
        self.stop()

    def _run_worker(self, worker_id):
        """Entry point of worker thread.

        Args:
            worker_id (int): increment ID useful to identify the thread.
        """
        threading.current_thread().name = 'Worker %s #%s' % (
            self._worker_name, worker_id)
        return self._fn(self.context)

    def _handle_worker_ending(self, worker_id, future):
        """Called after a worker just stopped.

        If it's an uncaught exception, a new worker is restarted.

        Args:
            worker_id (int): id of the terminated worker.
            future (concurrent.Future)
        """

        error = future.exception()

        if error:
            _logger.critical("Worker %s #%s has crashed: %s",
                             self._worker_name, worker_id, error)
            with self.context:
                if not self.context.stop_order:
                    self._last_worker_id += 1
                    future = self._executor.submit(self._run_worker,
                                                   self._last_worker_id)
                    done_handler = functools.partial(
                        self._handle_worker_ending,
                        self._last_worker_id)
                    future.add_done_callback(done_handler)
        else:
            _logger.debug("Worker %s has returned.", self._worker_name)
