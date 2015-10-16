# -*- coding: utf-8 -*-


def is_thenable(value):
    """Check if an object can be chained, like a Promise, or is a "result".

    The promise module uses this function to differentiate "chainable" objects
    and direct return values, when using a callback who can returns both.

    Returns:
        boolean: True if the value has an attribute 'then' who is callable.
            False if not.
    """
    return hasattr(getattr(value, 'then', None), '__call__')


def is_cancellable(value):
    """Check if an object (thenable) can be cancelled (has a cancel() method).

    Args:
        value: object to test, usually a Promise.
    Returns:
        boolean: True if it can be cancelled, False if not.
    """
    return hasattr(getattr(value, 'cancel', None), '__call__')
