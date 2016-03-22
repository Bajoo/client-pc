# -*- coding: utf-8 -*-

import requests
import requests.packages.urllib3 as urllib3

from .errors import NetworkError
from .request import Request


class StatusTable(object):
    """Table containing networks status and shares error states.

    An instance of StatusTable keep information on the network state, prevents
    requests to be sent if they will fails (to avoid flooding the network), and
    informs others of network changes.

    Attributes:
        general_error (Exception): if None, the network is operational.
            Otherwise, contains the last global network error.
        host_errors (dict): a list of status per host. The key is the HTTP host
            (eg: storage.bajoo.fr) and the value is the current Error, or None
            if there is no error.
    """

    def __init__(self, health_checker):
        """StatusTable constructor

        Args:
            health_checker (HealthChecker): on-demand utility to check server
                connectivity.
        """
        self.general_error = None
        self.host_errors = {}

        self._health_checker = health_checker

    def reject_request(self, request):
        """Check if a request should be allowed or not.

        The purpose of rejecting requests is to prevents flooding the network
        when there is a problem, as well as rejecting network promises faster
        than if the request have been sent.

        Args:
            request (Request): request which will be send.
        Returns:
            Exception: If the network is in error, returns the last exception
                raised. If the request can be sent, returns None
        """
        if request.action is Request.PING:
            return None

        if self.general_error:
            return self.general_error

        return self.host_errors.get(request.host, None)

    def update(self, request, error=None):
        """Update status according to the result of the request.

        Args:
            request (Request): request terminated (either by successfully
                returning a result, or by raising a exception).
            error (Exception, optional): exception raised by the request, if
                any.
        """
        if not error:
            return self._remove_error(request.host)

        # To retrieve information on what has really happened, we must find the
        # source error. The errors can be encapsulated in many layers
        # (socket -> urllib3 -> retry -> requests -> bajoo).
        source_error = error

        if isinstance(source_error, NetworkError):
            source_error = source_error.reason

        if isinstance(source_error, requests.ConnectionError):
            urllib_err = source_error.args[0]

            # If we use the "retry" option from requests, real errors are
            # encapsulated in a MaxRetryError
            if isinstance(urllib_err, urllib3.exceptions.MaxRetryError):
                urllib_err = urllib_err.reason

            if isinstance(urllib_err, urllib3.exceptions.ProxyError):
                # This is a global error, no matter what is the inner problem.

                # TODO: better message extraction.
                # user_message = urllib_err.args[0]
                # cause = urllib_err.args[1]  # socket.error

                return self._set_error(error, request)

            elif isinstance(urllib_err, urllib3.exceptions.ProtocolError):
                err = urllib_err.args[1]

                errno = getattr(err, 'errno', 0)
                # errno 101: network unreachable: global error
                # errno 111: connexion refused: per-host problem
                # errno 113: no route to host: probably a global error
                # errno -2 (socket.gaierror): probably a DNS error

                if errno is 101:
                    return self._set_error(error, request)
                elif errno is 111:
                    return self._set_error(error, request,
                                           general=False, host=True)
                else:
                    return self._set_error(error, request, host=True)

            elif isinstance(urllib_err,
                            urllib3.exceptions.ConnectTimeoutError):
                return self._set_error(error, request,
                                       general=False, host=True)

            else:  # generic case ConnectionError
                return self._set_error(error, request, host=True)

        if isinstance(source_error, requests.HTTPError):
            # TODO: handle 5XX errors
            # if error.response.status_code < 500:
            return self._remove_error(request.host)

        # At this point it's an unknown error
        return self._set_error(error, request, host=True)

    def _set_error(self, error, request, general=True, host=False):
        if general:
            self.general_error = error
        if host:
            self.host_errors[request.host] = error

        self._health_checker.check('%s://%s' % (request.scheme, request.host))

    def _remove_error(self, host=None):
        self.general_error = None
        if host:
            self.host_errors.pop(host, None)
