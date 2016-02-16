# -*- coding: utf-8 -*-

from collections import deque
from concurrent.futures import ThreadPoolExecutor
import logging
import sys
from threading import Condition, current_thread
from ..promise import Promise, is_thenable

_logger = logging.getLogger(__name__)


_MAX_WORKER = 5
_executor = None
_task_condition = Condition()
_stop_order = False

# The non-started tasks are stored in `_task_queue` (both high and low
# priority). The started segmented tasks are stored in `_split_task_queue`.
_split_task_queue = deque()
_task_queue = deque()

_last_worker_id = 0


def start():
    global _executor, _stop_order, _last_worker_id

    def _clean_and_restart(future):
        global _last_worker_id

        error = future.exception()

        if error:
            _logger.critical('Filesync task worker has crashed: %s' % error)
            with _task_condition:
                if not _stop_order:
                    _last_worker_id += 1
                    future = _executor.submit(_run_worker, _last_worker_id)
                    future.add_done_callback(_clean_and_restart)

    _executor = ThreadPoolExecutor(max_workers=_MAX_WORKER)
    _stop_order = False

    for i in range(_MAX_WORKER):
        _last_worker_id += 1
        f = _executor.submit(_run_worker, _last_worker_id)
        f.add_done_callback(_clean_and_restart)


def stop():
    """Stop all operations as soon as possible."""
    with _task_condition:
        global _stop_order
        _stop_order = True
        _task_condition.notify_all()
    if _executor:
        _executor.shutdown()


class Context(object):
    def __enter__(self):
        start()

    def __exit__(self, type, value, tb):
        stop()


def add_task(task, priority=False):
    """Add a task to the list.

    The task is a coroutine who performs IO-bound tasks. It can performs in
    many "steps", separated by external calls using Promise yielded.
    The first yielded result who is not a thenable (see promise.is_thenable())
    is used to resolve the returning promise.

    The initialization phase of the task is executed immediately, in the caller
    thread. It allow the task to performs init operation sooner (typically, to
    discard other tasks who are no longer useful).
    IO-bound operations shouldn't be done before the first yield.

    Each following call to the generator is guaranteed to be executed in the
    Task consumer context, with thread dedicated to IO-bound operations.

    Args:
        task (callable): A task is a callable who returns a generator. Each
            time the generator yield a Promise, the generator is registered to
            be called as soon as the promise resolve.
            The task is considered done when it yield a non-Promise value.
        priority (boolean, optional): if True, the task is set on top of the
            queue.
    Returns:
        Promise: Promise resolved when the task is done. If the task fails
            (raises an exception), the Promise is rejected with this exception.
    """
    def task_executor(resolve, reject):
        gen = task()
        try:
            result = next(gen)
        except StopIteration:
            resolve(None)
        except:
            reject(*sys.exc_info())
        else:
            _call_next_or_set_result(resolve, reject, gen, result, priority)

    return Promise(task_executor)


def _iter_generator(resolve, reject, gen, value):
    """Execute the next step of a task generator."""
    try:
        result = gen.send(value)
    except StopIteration:
        resolve(value)
    except:
        reject(*sys.exc_info())
    else:
        _call_next_or_set_result(resolve, reject, gen, result)


def _iter_generator_error(resolve, reject, gen, reason):
    """Execute the next step of a task generator, due to a rejected Promise."""
    try:
        result = gen.throw(reason)
    except StopIteration:
        resolve(None)
    except:
        reject(*sys.exc_info())
    else:
        _call_next_or_set_result(resolve, reject, gen, result)


def _call_next_or_set_result(resolve, reject, gen, value, priority='SPLIT'):
    """When a task has yielded a value, prepare the next step, or resolve.

    If the value yielded is a thenable, then we register the next step in the
    task queue.
    Otherwise, the value is the task result, and so the task is fulfilled.

    Args:
        priority (bool or 'SPLIT', optional): If True, the task is of high
            priority. The 'SPLIT' priority means the task is split in several
            steps, and the next step should be called as soon as possible,
            before high priority tasks.
    """
    def register_iteration(new_value):
        with _task_condition:
            task = (resolve, reject, gen, new_value, False)
            if priority is 'SPLIT':
                _split_task_queue.append(task)
            elif priority:
                _task_queue.appendleft(task)
            else:
                _task_queue.append(task)
            _task_condition.notify()

    def register_iteration_error(reason):
        with _task_condition:
            task = (resolve, reject, gen, reason, True)
            if priority is 'SPLIT':
                _split_task_queue.append(task)
            elif priority:
                _task_queue.appendleft(task)
            else:
                _task_queue.append(task)
            _task_condition.notify()

    if is_thenable(value):
        value.then(register_iteration, register_iteration_error)
    else:
        resolve(value)
        gen.close()


def _run_worker(id):
    """Main loop of the workers (task consumers).

    Each Thread wait for tasks, then execute them and handles theirs yielded
    promises.

    Args:
        id (int): number of worker.
    """
    current_thread().name = 'Filesync worker %s' % id

    while True:
        with _task_condition:
            if _stop_order:
                return

            try:
                # in-progress tasks
                (resolve, reject,
                 generator, value, is_error) = _split_task_queue.popleft()
            except IndexError:
                # New tasks
                try:
                    (resolve, reject,
                     generator, value, is_error) = _task_queue.popleft()
                except IndexError:
                    _task_condition.wait()
                    continue

        if is_error:
            _iter_generator_error(resolve, reject, generator, value)
        else:
            _iter_generator(resolve, reject, generator, value)
