# -*- coding: utf-8 -*-

import logging
from threading import Timer, Lock

_logger = logging.getLogger(__name__)


class PeriodicTask(object):
    """Generic Thread-based service, executing a task at regular interval."""

    def __init__(self, name, delay, task, *args, **kwargs):
        """Constructor
        Args:
            name (str): Thread name.
            delay (int): Delay between two execution, in seconds
            task (callable): task to execute each periods.
            *args (optional): arguments passed to the task.
            **kwargs (optional): keywords arguments passed to the task.
        """
        self._delay = delay
        self._name = name
        self._task = task
        self._args = args
        self._kwargs = kwargs
        self._timer = None
        self._canceled = False
        self._lock = Lock()
        self._apply_now_callback = None

    def _exec_task(self, *args, **kwargs):
        with self._lock:
            try:
                self._args = self._task(*args, **kwargs)
            except:
                _logger.exception('Periodic task %s has raised exception' %
                                  self._task)
            self._timer = Timer(self._delay, self._exec_task, args=self._args)
            self._timer.name = self._name
            self._timer.daemon = True
            if not self._canceled:
                self._timer.start()
            callback = self._apply_now_callback
            self._apply_now_callback = None
        if callback:
            callback()

    def start(self):
        """Start the task.

        The first execution is immediate.
        """
        _logger.debug('Start periodic task %s', self._task)
        self._timer = Timer(0, self._exec_task, args=self._args)
        self._timer.name = self._name
        self._timer.daemon = True
        self._timer.start()

    def stop(self):
        """Stop the task.

        Note that if the function is running at the moment this method is
        called, the current iteration cannot be stopped.
        """
        _logger.debug('Stop periodic task %s', self._task)
        self._canceled = True
        self._timer.cancel()

    def apply_now(self, callback=None):
        """Apply the task as soon as possible.

        Note that if the task is currently running, it will wait the end, then
        another iteration will be executed immediately after that.

        Args:
            callback (Callable, optional): if set, called when we're sure the
                task as been done.
        """
        self._timer.cancel()
        with self._lock:
            self._timer.cancel()  # In case the task has replaced the _timer.

            self._timer = Timer(0, self._exec_task, args=self._args)
            self._timer.name = self._name
            self._timer.daemon = True
            self._apply_now_callback = callback
            self._timer.start()
