# -*- coding: utf-8 -*-

from collections import deque
import logging
import sys
from ..generic_executor import GenericExecutor, SharedContext
from ..promise import Promise, is_thenable

_logger = logging.getLogger(__name__)

_MAX_SIMULTANEOUS_TASK = 100
_MAX_WORKER = 5

_executor = None


class FilesyncContext(SharedContext):
    """Custom context for filesync workers

    Attributes:
        nb_ongoing_tasks (int): number of started tasks. It includes all tasks
            in `ongoing_task_queue`, but also tasks who are not in any task
            queue (Promises not yet resolved).
        ongoing_task_queue (deque): List of started, segmented tasks, waiting
            for the next step.
        task_queue (deque): non-started tasks (both high and low priority).
    """

    def __init__(self):
        super(FilesyncContext, self).__init__()
        self.nb_ongoing_tasks = 0
        self.ongoing_task_queue = deque()
        self.task_queue = deque()


def start():
    global _executor
    if not _executor:
        _executor = GenericExecutor('filesync', _MAX_WORKER, _run_worker,
                                    FilesyncContext())
    _executor.start()


def stop():
    """Stop all operations as soon as possible."""
    if _executor:
        _executor.stop()


def add_task(task, priority=False):
    """Add a task to the list.

    The task is a coroutine who performs IO-bound tasks. It can performs in
    many "steps", separated by external calls using Promise yielded.
    The first yielded result who is not a thenable (see promise.is_thenable())
    is used to resolve the returning promise.

    Each call to the generator is guaranteed to be executed in the
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
        with _executor.context as ctx:
            gen_task = (resolve, reject, gen)
            if priority:
                ctx.task_queue.appendleft(gen_task)
            else:
                ctx.task_queue.append(gen_task)
            _executor.context.condition.notify()

    return Promise(task_executor)


def _start_generator(context, resolve, reject, gen):
    try:
        result = next(gen)
    except StopIteration:
        resolve(None)
    except:
        reject(*sys.exc_info())
    else:
        with context:
            context.nb_ongoing_tasks += 1
        _call_next_or_set_result(context, resolve, reject, gen, result)


def _iter_generator(context, resolve, reject, gen, value):
    """Execute the next step of a task generator."""
    try:
        result = gen.send(value)
    except StopIteration:
        with context:
            context.nb_ongoing_tasks -= 1
        resolve(value)
    except:
        with context:
            context.nb_ongoing_tasks -= 1
        reject(*sys.exc_info())
    else:
        _call_next_or_set_result(context, resolve, reject, gen, result)


def _iter_generator_error(context, resolve, reject, gen, reason):
    """Execute the next step of a task generator, due to a rejected Promise."""
    try:
        result = gen.throw(reason)
    except StopIteration:
        with context:
            context.nb_ongoing_tasks -= 1
        resolve(None)
    except:
        with context:
            context.nb_ongoing_tasks -= 1
        reject(*sys.exc_info())
    else:
        _call_next_or_set_result(context, resolve, reject, gen, result)


def _call_next_or_set_result(context, resolve, reject, gen, value):
    """When a task has yielded a value, prepare the next step, or resolve.

    If the value yielded is a thenable, then we register the next step in the
    task queue.
    Otherwise, the value is the task result, and so the task is fulfilled.
    """
    def register_iteration(new_value):
        with context:
            task = (resolve, reject, gen, new_value, False)
            context.ongoing_task_queue.append(task)
            context.condition.notify()

    def register_iteration_error(reason):
        with context:
            task = (resolve, reject, gen, reason, True)
            context.ongoing_task_queue.append(task)
            context.condition.notify()

    if is_thenable(value):
        value.then(register_iteration, register_iteration_error)
    else:
        with context:
            context.nb_ongoing_tasks -= 1
        resolve(value)
        gen.close()


def _run_worker(context):
    """Main loop of the workers (task consumers).

    Each Thread wait for tasks, then execute them and handles theirs yielded
    promises.

    Args:
        context (FilesyncContext): context shared between workers.
    """

    while True:
        with context as ctx:
            if ctx.stop_order:
                return

            # Try to execute ongoing tasks
            is_ongoing_task = None
            try:
                (resolve, reject,
                 generator, value, is_error) = ctx.ongoing_task_queue.popleft()
                is_ongoing_task = True
            except IndexError:
                # Else, begin the next new task
                if ctx.nb_ongoing_tasks < _MAX_SIMULTANEOUS_TASK:
                    try:
                        (resolve, reject, generator) = ctx.task_queue.popleft()
                        is_ongoing_task = False
                    except IndexError:
                        pass

            if is_ongoing_task is None:
                # No task to execute.
                ctx.condition.wait()
                continue

        if not is_ongoing_task:
            _start_generator(ctx, resolve, reject, generator)
        elif is_error:
            _iter_generator_error(ctx, resolve, reject, generator, value)
        else:
            _iter_generator(ctx, resolve, reject, generator, value)


def Context():
    global _executor
    _executor = GenericExecutor('filesync', _MAX_WORKER, _run_worker,
                                FilesyncContext())
    return _executor
