# -*- coding: utf-8 -*-

from threading import Lock, Timer

from ..promise import Deferred, CancelledError
from .request import Request


class HealthChecker(object):
    """Track status of "broken" servers by sending ping requests.

    Attributes:
        _hosts (dict): a map uri <-> Promise.
    """
    def __init__(self, execute_request):
        """HealthChecker constructor

        Args:
            execute_request (callable): function which will execute the
                request. It must take a Request instance in argument, and
                returns a Promise (resolved when the request is done).
        """
        self._lock = Lock()
        self._hosts = {}
        self._execute_task = execute_request

    def check(self, url):
        """Start a series of checks until the host responds.

        A "ping" request is sent regularly until the hosts responds.
        If the target server never responds, then the promise will never
        resolve.

        If the url is already under check, the same promise as the first call
        is returned.

        Args:
            url (str): eg: "https//www.bajoo.fr",
                or "http://www.example.com:8080"
        Returns:
            Promise: Will resolve as soon as the host accepts HTTP requests
                The promise can't be rejected.
        """
        with self._lock:
            if url in self._hosts:
                return self._hosts[url]['deferred'].promise
            df = Deferred()
            self._hosts[url] = {'deferred': df, 'timer': None}

        self._start_request(url)
        return df.promise

    def _start_request(self, url, counter=0):
        req = Request(Request.PING, 'OPTIONS', url, priority=5)
        p = self._execute_task(req)
        p.then(lambda _res: self._on_ping_succeed(url),
               lambda _res: self._on_ping_fails(url, counter))

    def _on_ping_succeed(self, url):
        with self._lock:
            df = self._hosts.pop(url, {}).get('deferred', None)
        if df:
            df.resolve(None)

    def _on_ping_fails(self, url, counter):
        # Exponential delay between 2 pings.
        if counter < 9:
            delay = 0.5 * (2 ** counter)
        else:
            delay = 300

        with self._lock:
            if url not in self._hosts:
                return  # Check has been cancelled.

            t = Timer(delay, self._start_request, args=[url, counter + 1])
            t.name = 'HealthCheck Timer <%s> #%s' % (url, counter + 1)
            t.daemon = True
            self._hosts[url]['timer'] = t
        t.start()

    def stop(self):
        """Stop all current checks."""
        threads = []
        with self._lock:
            for check in self._hosts.values():
                check['timer'].cancel()
                threads.append(check['timer'])
                check['deferred'].reject(CancelledError())
            self._hosts = {}

        for t in threads:
            try:
                t.join()
            except RuntimeError:
                pass
