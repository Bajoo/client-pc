# -*- coding: utf-8 -*-

import heapq
import logging
import sys
from ..generic_executor import GenericExecutor, SharedContext
from .request import upload, download, json_request
from ..promise import Promise

_logger = logging.getLogger(__name__)

_MAX_WORKERS = 5
_executor = None


class NetworkSharedContext(SharedContext):
    """

    Attributes:
        requests (heapq): list of requests not yet started. Each element is a
            tuple: (priority, counter, resolve, reject, action, verb, url,
            params).
        counter (int): value incremented for each task added. It's used to give
            priority to the oldest tasks (at equal priority value).
    """
    def __init__(self):
        super(NetworkSharedContext, self).__init__()
        self.requests = []
        self.counter = 0


def start():
    global _executor

    if not _executor:
        _executor = GenericExecutor('network', _MAX_WORKERS, _run_worker,
                                    NetworkSharedContext())
    _executor.start()


def stop():
    if _executor:
        _executor.stop()


def add_task(action, verb, url, params, priority=100):
    """Add a request to send.

    Args:
        action (str): type of the request. Should be one of 'UPLOAD',
            'DOWNLOAD' or 'QUERY'
        verb (str): HTTP verb
        url (unicode): url
        params (dict): optional arguments passed as **kwargs.
        priority (int, optional): default to 100. Smallest values are executed
            first.
    Returns:
        Promise<???>
    """
    _logger.log(5, "Add request %s %s", verb, url)

    def execute_request(resolve, reject):
        with _executor.context:
            task = (priority, _executor.context.counter, resolve, reject,
                    action, verb, url, params)
            heapq.heappush(_executor.context.requests, task)
            _executor.context.counter += 1
            _executor.context.condition.notify()

    return Promise(execute_request)


def _run_worker(context):
    """Network worker main loop

    Args:
        context (NetworkSharedContext)
    """
    action_mapping = {
        'UPLOAD': upload,
        'DOWNLOAD': download,
        'REQUEST': json_request
    }

    while True:
        with context:
            if context.stop_order:
                return
            try:
                (_priority, _counter, resolve, reject,
                 action, verb, url, params) = heapq.heappop(context.requests)
            except IndexError:
                context.condition.wait()
                continue

        try:
            action_fn = action_mapping[action]
        except KeyError:
            _logger.error("Unknown action '%s' for request: %s %s",
                          action, verb, url)
            reject(ValueError('Request with unknown type %s' % action))
            continue

        _logger.log(5, "Start request %s %s", verb, url)
        try:
            result = action_fn(verb, url, **params)
        except:
            reject(*sys.exc_info())
        else:
            resolve(result)
        _logger.log(5, "request %s %s completed", verb, url)
