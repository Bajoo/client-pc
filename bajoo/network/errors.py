# -*- coding: utf-8 -*-
"""This module defines all errors which can occur in the network module.

requests exceptions can be converted to bajoo.network errors using the
``handler`` decorator.

Bajoo errors have a human-readable message, ready to be displayed.
They are also more verbose when displayed using 'repr()`.
"""

import logging
import requests.exceptions

from ..common.i18n import N_


_logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Base class for bajoo.network errors.

    Attributes:
        message (str): Human readable message, describing the error.
    """

    def __init__(self, error, message=None):
        """
        Args:
            error: base error
        """
        self.message = message or N_("A network error has occurred.")
        Exception.__init__(self, self.message)
        self.data = error

class ConnectionError(NetworkError):
    def __init__(self, error):
        NetworkError.__init__(self, error,
                              N_("Unable to connect to the Bajoo servers."))


class ConnectTimeoutError(NetworkError):
    def __init__(self, error):
        NetworkError.__init__(self, error,
                              N_("The server did not respond on time."))


class HTTPError(NetworkError):
    """Base class for HTTP errors.

    The class can be displayed for debug, using ``repr(error)``.

    Attributes:
        code (int): HTTP status code
        reason (str): HTTP status text
        request (str): representation of the request.
        response (dict or text): If the response content was in json, the
            corresponding dict, else the content as text.
        err_code (str): If response is a standard Bajoo error, the Bajoo error
            code.
        err_description (str): If response is a standard Bajoo error, the Bajoo
            error description.
        err_data: If response is a standard Bajoo error, the data
            associated to the error, if any.
    """
    def __init__(self, error, message=None):
        """
        Args:
            error (requests.exceptions.HTTPError): base error.
        """
        if not message:
            message = (N_("The server has returned an HTTP error: %s %s") %
                       (error.response.status_code, error.response.reason))

        NetworkError.__init__(self, error, message)

        self.code = error.response.status_code
        self.reason = error.response.reason
        self.request = '%s %s' % (error.request.method, error.request.url)
        self.err_code = None
        self.err_description = None
        self.err_data = None

        try:
            self.response = self.data.response.json()
            self.err_code = self.response.get('error')
            self.err_description = self.response.get('error_description')
            self.err_data = self.response.get('error_data')
        except ValueError:
            self.response = self.data.response.text

    def __repr__(self):
        if self.err_code:
            response = '\n'.join((
                '\tResponse:',
                '\t\tcode: "%s"' % self.err_code,
                '\t\tdescription: "%s"' % self.err_description,
                '\t\tdata: "%s"' % self.err_data))
        else:
            response = '\tResponse: %s' % self.response

        return '\n'.join(("HTTP Error: %s %s" % (self.code, self.reason),
                          "\tRequest: %s" % self.request,
                          response))


class HTTPBadRequestError(HTTPError):
    def __init__(self, error):
        message = N_("The HTTP request is invalid. This is a bug, "
                     "either in the client or in the server. "
                     "Sorry for the inconvenience :(")
        HTTPError.__init__(self, error, message)


class HTTPUnauthorizedError(HTTPError):
    def __init__(self, error):
        # Note: although it's not always the case, the expired session is the
        # only case the user should read this message.
        message = N_("Your session has expired.")
        HTTPError.__init__(self, error, message)


class HTTPForbiddenError(HTTPError):
    def __init__(self, error):
        message = N_("You don't have the permission to do this "
                     "operation.")
        HTTPError.__init__(self, error, message)


class HTTPNotFoundError(HTTPError):
    def __init__(self, error):
        message = N_("The element you're looking for has not been found.")
        HTTPError.__init__(self, error, message)


class HTTPInternalServerError(HTTPError):
    def __init__(self, error):
        message = N_("The Bajoo servers have encountered "
                     "an unexpected error :(")
        HTTPError.__init__(self, error, message)


class HTTPNotImplementedError(HTTPError):
    def __init__(self, error):
        message = N_("Bajoo service does not understand or "
                     "does not support this function.")
        HTTPError.__init__(self, error, message)


class HTTPServiceUnavailableError(HTTPError):
    def __init__(self, error):
        message = N_("The Bajoo servers are temporarily unavailable. "
                     "Please try again later.")
        HTTPError.__init__(self, error, message)


_code2error = {
    400: HTTPBadRequestError,
    401: HTTPUnauthorizedError,
    403: HTTPForbiddenError,
    404: HTTPNotFoundError,
    500: HTTPInternalServerError,
    501: HTTPNotImplementedError,
    503: HTTPServiceUnavailableError
}


def handler(func):
    """Decorator who handles errors of the requests.

    Converts requests.exceptions.* into bajoo.network.errors.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError as error:
            raise ConnectionError(error)
        except (requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout) as error:
            raise ConnectTimeoutError(error)
        except requests.exceptions.HTTPError as error:
            err_class = _code2error.get(error.response.status_code, HTTPError)
            raise err_class(error)
        except requests.exceptions.RequestException as error:
            raise NetworkError(error)

    return wrapper
