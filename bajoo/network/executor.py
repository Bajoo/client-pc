# -*- coding: utf-8 -*-

import heapq
import logging
import sys
from ..generic_executor import GenericExecutor, SharedContext
from .errors import NetworkError
from .request import Request
from .send_request import upload, download, json_request
from .status_table import StatusTable
from ..promise import Deferred

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
        self.status = StatusTable()


def start():
    global _executor

    if not _executor:
        _executor = GenericExecutor('network', _MAX_WORKERS, _run_worker,
                                    NetworkSharedContext())
    _executor.start()


def stop():
    if _executor:
        _executor.stop()


def add_task(request):
    """Add a request to send.

    Args:
        request (Request)
    Returns:
        Promise
    """
    _logger.log(5, "Add request %s", request)
    df = Deferred()
    with _executor.context:
        request.increment_id = _executor.context.counter
        task = (request, df)
        heapq.heappush(_executor.context.requests, task)
        _executor.context.counter += 1
        _executor.context.condition.notify()

    return df.promise


def _run_worker(context):
    """Network worker main loop

    Args:
        context (NetworkSharedContext)
    """
    action_mapping = {
        Request.UPLOAD: upload,
        Request.DOWNLOAD: download,
        Request.JSON: json_request,
        Request.PING: json_request
    }

    while True:
        with context:
            if context.stop_order:
                return
            try:
                (request, deferred) = heapq.heappop(context.requests)
            except IndexError:
                context.condition.wait()
                continue

            if not context.status.allow_request(request):
                # TODO: custom exception
                deferred.reject(NetworkError(
                    message='The request has been rejected, because there is '
                            'a network error'))
                continue

        try:
            action_fn = action_mapping[request.action]
        except KeyError:
            _logger.error("Unknown action for request: %s", request)
            deferred.reject(ValueError('Request with unknown type %s' %
                                       request.action))
            continue

        _logger.log(5, "Start request %s", request)
        try:
            result = action_fn(request)
        except Exception as error:
            context.status.update(request, error)
            deferred.reject(*sys.exc_info())
        else:
            context.status.update(request)
            deferred.resolve(result)
        _logger.log(5, "request %s completed", request)
