# -*- coding: utf-8 -*-

from .promise import Promise
from .util import is_thenable


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


def resolve_rec(result):
    """Recursively resolve the promise if it returns another Promise.

    In same case, an asynchronous action must be done in many steps, not known
    at start. resolve_rec() allow a Promise to resolve itself as another
    Promise object (the next step), and so recursively.

    Returns:
        Promise<?>: Promise guaranteed to resolve a non-promise result.
    """
    if is_thenable(result):
        return result.then(resolve_rec)
    else:
        return Promise.resolve(result)
