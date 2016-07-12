# -*- coding: utf-8 -*-

from . import executor
from ..common import config
from .proxy import prepare_proxy
from .request import Request


class Service(object):
    """HTTP network service.

    It's a "facade" pattern, providing a public interface to all complex
    network-related operations.
    """

    def __init__(self):
        self._executor = None

    def start(self):
        self._executor = executor.Executor()

        # Initial set of proxy settings.
        proxy_mode = config.get('proxy_mode')
        settings = {
            'type': config.get('proxy_type'),
            'url': config.get('proxy_url'),
            'port': config.get('proxy_port'),
            'user': config.get('proxy_user'),
            'password': config.get('proxy_password')
        }
        self.set_proxy(proxy_mode, settings)

        self._executor.start()

    def stop(self):
        self._executor.stop()
        self._executor = None

    def _add_task(self, request):
        return self._executor.add_task(request)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def json_request(self, verb, url, priority=10, **params):
        """
        Send a request and get the json from its response.

        Args:
            verb: (str)
            url: (str)
            priority (int, optional): requests with lower priority are executed
                first. Default to 10 (high priority)
            params: additional parameters
        Returns: Future<dict>
            A Future object containing the json object from the response
        """
        params = dict(params)
        request = Request(Request.JSON, verb, url, params, priority=priority)
        return self._add_task(request)

    def download(self, verb, url, priority=100, **params):
        """
        Download a file and save it as a temporary file.

        Args:
            verb: (str)
            url: (str)
            priority (int, optional): requests with lower priority are executed
                first. Default to 100 (normal priority)
            params: additional parameters
        Returns: Future<File>
            A Future object contains the temporary file object
        """
        params = dict(params)
        request = Request(Request.DOWNLOAD, verb, url, params,
                          priority=priority)
        return self._add_task(request)

    def upload(self, verb, url, source, priority=100, **params):
        """
        Upload a file to an address.

        Note: if a file-like object is passed as source, it will be
        automatically closed after the upload.

        Args:
            verb: (str)
            url: (str)
            source (str/File): Path of the file to upload (if type is str), or
                file-like object to upload.
            priority (int, optional): requests with lower priority are executed
                first. Default to 100 (normal priority)
            params: additional parameters
        """
        params = dict(params)
        request = Request(Request.UPLOAD, verb, url, params, source, priority)
        return self._add_task(request)

    def set_proxy(self, proxy_mode, settings=None):
        """Set proxy settings.

        Settings applies to all requests. They are kept until the next
        set_proxy() call.

        Args:
            proxy_mode (str): Indicate from where the proxy settings are
                obtained. Must be one of 'system_settings', 'manual_settings',
                or 'no_proxy'.
            settings (dict, optional): in 'manual_settings' mode, effective
                proxy settings. In other modes, this argument is ignored.
                It uses the following config settings (all are required):
                - type
                - url
                - port
                - user
                - password

        """
        with self._executor.context as context:
            context.proxy_settings = prepare_proxy(proxy_mode, settings)
