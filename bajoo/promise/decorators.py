# -*- coding: utf-8 -*-

from .promise import Promise


def wrap_promise(f):
    """Decorator who converts the result in a Promise object.

    If the function decorated returns a thenable, it's transmitted as is.
    Else, a new Promise is created with the returned value as result.
    """
    def wrapper(*args, **kwargs):
        try:
            return Promise.resolve(f(*args, **kwargs))
        except Exception as error:
            return Promise.reject(error)

    return wrapper
