# -*- coding: utf-8 -*-

import heapq
import logging
import sys

import requests
from requests import __version__ as requests_version

from .. import __version__ as bajoo_version
from ..generic_executor import GenericExecutor, SharedContext
from .health_checker import HealthChecker
from .request import Request
from .send_request import upload, download, json_request
from .status_table import StatusTable
from ..promise import Deferred

_logger = logging.getLogger(__name__)

_MAX_WORKERS = 10

# Maximum number of automatic retry in case of connexion error
# HTTP errors (4XX and 5XX) are not retried.
MAX_RETRY = 3


class NetworkSharedContext(SharedContext):
    """

    Attributes:
        requests (heapq): list of requests not yet started. Each element is a
            tuple: (priority, counter, resolve, reject, action, verb, url,
            params).
        counter (int): value incremented for each task added. It's used to give
            priority to the oldest tasks (at equal priority value).
        proxy_settings (dict): proxy settings
    """

    def __init__(self, execute_request):
        """
        Attributes:
            execute_request (callable): function which will execute the
                request. See HealthChecker doc.

        """
        super(NetworkSharedContext, self).__init__()
        self.requests = []
        self.counter = 0
        self.health_checker = HealthChecker(execute_request)
        self.status = StatusTable(self.health_checker)
        self.proxy_settings = None
        self.session = self._prepare_session()

    def _prepare_session(self):
        """Prepare a session to send an HTTP(S) request, with auto retry.

        Returns:
            requests.Session: new HTTP(s) session
        """
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRY)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'timeout': 4,
            'User-Agent': 'Bajoo-client/%s python-requests/%s' % (
                bajoo_version, requests_version)
        })
        return session


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

            last_error = context.status.reject_request(request)
            if last_error:
                # request "rejected"
                deferred.reject(last_error)
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
            result = action_fn(request, context.session,
                               context.proxy_settings)
        except Exception as error:
            with context:
                context.status.update(request, error)
            deferred.reject(*sys.exc_info())
        else:
            with context:
                context.status.update(request)
            deferred.resolve(result)
        _logger.log(5, "request %s completed", request)


class Executor(GenericExecutor):

    def __init__(self):
        context = NetworkSharedContext(self.add_task)
        super(Executor, self).__init__('network', _MAX_WORKERS,
                                       _run_worker, context)

    def add_task(self, request):
        """Add a request to send.

        Args:
            request (Request)
        Returns:
            Promise
        """
        _logger.log(5, "Add request %s", request)
        df = Deferred()
        with self.context:
            request.increment_id = self.context.counter
            task = (request, df)
            heapq.heappush(self.context.requests, task)
            self.context.counter += 1
            self.context.condition.notify()

        return df.promise
