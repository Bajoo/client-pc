# -*- coding: utf-8 -*-
"""This module defines all errors which can occur in the network module.

requests exceptions can be converted to bajoo.network errors using the
``handler`` decorator.

Bajoo errors have a human-readable message, ready to be displayed.
They are also more verbose when displayed using 'repr()`.
"""

import logging
import requests.exceptions

_logger = logging.getLogger(__name__)


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
            # TODO: raise the corresponding subclass of HTTPError.
            raise HTTPError(error)
        except requests.exceptions.RequestException as error:
            raise NetworkError(error)

    return wrapper


class NetworkError(Exception):
    def __init__(self, error):
        """
        Args:
            error: base error
        """
        self.data = error

        if not self.message:
            self.message = "A network error has occurred."

        _logger.exception(self.message)


class ConnectionError(NetworkError):
    def __init__(self, error):
        self.message = "Unable to connect to the Bajoo servers."
        NetworkError.__init__(self, error)


class ConnectTimeoutError(NetworkError):
    def __init__(self, error):
        self.message = "The server did not respond on time."
        NetworkError.__init__(self, error)


class HTTPError(NetworkError):
    def __init__(self, error):
        """
        Args:
            error (requests.exceptions.HTTPError): base error.
        """
        if not hasattr(self, 'name') or \
                not self.name:
            self.name = "HTTP Error"

        if not self.message:
            self.message = "The server has returned an HTTP error: %s" % \
                           error.response.status_code

        self.code = error.response.status_code
        NetworkError.__init__(self, error)

    def __repr__(self):
        json = self.data.response.json()
        request = self.data.request

        return ("HTTP Error: %s %s\n"
                "\tRequest: %s %s\n"
                "\tResponse:\n"
                "\t\tcode: %s\n"
                "\t\tmessage: %s\n"
                "\t\tdata: %s") % \
               (self.code, self.name,
                request.method, request.url,
                json.code, json.message, json.data)


class HTTPBadRequestError(HTTPError):
    def __init__(self, error):
        self.name = "Bad Request"
        self.message = "The HTTP request is invalid. " \
                       "This is a bug, " \
                       "either in the client or in the server. " \
                       "Sorry for the inconvenience :("
        HTTPError.__init__(self, error)


class HTTPUnauthorizedError(HTTPError):
    def __init__(self, error):
        self.name = "Unauthorized"
        self.message = "Your session has expired."
        HTTPError.__init__(self, error)


class HTTPForbiddenError(HTTPError):
    def __init__(self, error):
        self.name = "Forbidden"
        self.message = "You don't have the permission to do this operation."
        HTTPError.__init__(self, error)


class HTTPNotFoundError(HTTPError):
    def __init__(self, error):
        self.name = "Not Found"
        self.message = "The element you're looking for has not been found."
        HTTPError.__init__(self, error)


class HTTPInternalServerError(HTTPError):
    def __init__(self, error):
        self.name = "Internal Server"
        self.message = "The Bajoo servers have encountered " \
                       "an unexpected error :("
        HTTPError.__init__(self, error)


class HTTPNotImplementedError(HTTPError):
    def __init__(self, error):
        self.name = "Not Implemented"
        self.message = "Bajoo service does not understand or " \
                       "does not support this function."
        HTTPError.__init__(self, error)


class HTTPServiceUnavailableError(HTTPError):
    def __init__(self, error):
        self.name = "Service Unavailable"
        self.message = "The Bajoo servers are temporarily unavailable. " \
                       "Please try again later."
        HTTPError.__init__(self, error)
