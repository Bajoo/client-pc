# -*- coding: utf-8 -*-

import logging
from threading import Timer, Lock
from ..promise import Deferred, CancelledError

_logger = logging.getLogger(__name__)


class PeriodicTask(object):
    """Generic Thread-based service, executing a task at regular interval.

    The task is executed first right after the call to `start()`, in a new
    thread.
    After each execution, the next execution is scheduled after the specified
    delay. The delay doesn't include the task's duration.

    Attributes:
        delay (int): delay between two executions, in seconds. When modified,
            the new value will be used only after the next execution.
        context (dict): dict that can be used as a scope shared between the
            multiple executions and/or the caller.
        args (tuple): arguments passed to the task.
        kwargs (dict): keyword arguments passed to the task.

    Note:
        context, args and kwargs attributes are not thread-safe. If needed, the
        sync mechanisms (to avoid race conditions) are up to the user.

    Example:

        >>> def _task(pt, arg):
        ...     assert pt.context['value'] == 3
        ...     assert arg == 17
        >>> args = 1
        >>> task = PeriodicTask('MyTask', 1, _task, 17)
        >>> task.context['value'] = 3
        >>> task.start()
        >>> task.stop()

    """

    def __init__(self, name, delay, task, *args, **kwargs):
        """Constructor
        Args:
            name (str): Thread name.
            delay (float): Delay between two executions, in seconds
            task (Callable[[PeriodicTask, ...], T]): task to execute each
                periods. First argument is the PeriodicTask instance.
            *args (optional): arguments passed to the task.
            **kwargs (optional): keywords arguments passed to the task.
        """
        self.delay = delay
        self.context = {}
        self.args = args
        self.kwargs = kwargs

        self._name = name
        self._task = task
        self._timer = None
        self._canceled = False
        self._lock = Lock()
        self._is_running = False  # must be acceded only with self._lock
        self._apply_now = False
        self._deferred = None

    def _exec_task(self, *args, **kwargs):
        with self._lock:
            df = self._deferred
            self._deferred = None
            self._is_running = True

        # self._lock must be released during task execution.
        result, error = None, None
        try:
            result = self._task(self, *args, **kwargs)
        except BaseException as err:
            error = err
            _logger.exception('Periodic task %s has raised exception',
                              self._task)
        with self._lock:
            self._is_running = False

            if self._apply_now:
                delay = 0
                self._apply_now = False
            else:
                delay = self.delay

            self._timer = Timer(delay, self._exec_task, args=self.args,
                                kwargs=self.kwargs)
            self._timer.name = self._name
            self._timer.daemon = True
            if not self._canceled:
                self._timer.start()
        if df:
            if error is None:
                df.resolve(result)
            else:
                df.reject(error)

    def start(self):
        """Start the task.

        The first execution is immediate.
        """
        _logger.debug('Start periodic task %s', self._task)
        self._timer = Timer(0, self._exec_task, args=self.args,
                            kwargs=self.kwargs)
        self._timer.name = self._name
        self._timer.daemon = True
        self._timer.start()

    def stop(self, join=False):
        """Stop the task.

        Note that if the function is running at the moment this method is
        called, the current iteration cannot be stopped.

        Args:
            join (bool, optional): if True, will block until the running task
                finish. Default to False
        """
        _logger.debug('Stop periodic task %s', self._task)
        with self._lock:
            self._canceled = True
            self._timer.cancel()
            if self._deferred:
                self._deferred.reject(CancelledError('PeriodicTask stop now.'))
                self._deferred = None

        if join:
            self._timer.join()

    def apply_now(self):
        """Apply the task as soon as possible.

        Note that if the task is currently running, it will wait the end, then
        another iteration will be executed immediately after that.

        The method can be called from inside the task itself.

        Returns:
            Promise[T]: resolved when the task has returned. The promise
                resolves with the value returned by the task. If the task
                raises an exception, the promise is rejected.
        """
        self._timer.cancel()
        with self._lock:
            if self._deferred:
                # special case: twice or more apply_now() at the same time.
                return self._deferred.promise

            self._deferred = Deferred()
            if self._is_running:
                # We can't stop the current task, so we set a flag to rerun as
                # soon as the task returns.
                self._apply_now = True
            else:
                self._timer.cancel()
                self._timer = Timer(0, self._exec_task, args=self.args)
                self._timer.name = self._name
                self._timer.daemon = True
                self._timer.start()

        return self._deferred.promise
