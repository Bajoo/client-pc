# -*- coding: utf-8 -*-

import sys
from .deferred import Deferred
from .util import is_thenable


def reduce_coroutine(safeguard=False):
    """Decorator who converts a coroutine of promises into a single promise.

    The greatest interest is the ability to write a function in an
    synchronous-like style, using many asynchronous Promises.
    Whatever is the number of Promises or async calls used, the result will
    always be an unique Promise wrapping the whole process.

    Args:
        safeguard (boolean): if true, use `Promise.safeguard()` on the
            resulting promise.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            """
            Args:
                *args
                **kwargs
            Returns:
                Promise<*>
            """
            df = Deferred(_name='COROUTINE %s' % func.__name__)
            if safeguard:
                df.promise.safeguard()

            try:
                # Create generator; Initialization phase
                gen = func(*args, **kwargs)
            except:
                df.reject(*sys.exc_info())
                return df.promise

            def _call_next_or_set_result(value):
                if is_thenable(value):
                    value.then(iter_next, iter_error, exc_info=True)
                else:
                    gen.close()
                    return df.resolve(value)

            def iter_next(yielded_value):
                try:
                    next_value = gen.send(yielded_value)
                except StopIteration:
                    return df.resolve(yielded_value)
                except:
                    return df.reject(*sys.exc_info())
                _call_next_or_set_result(next_value)

            def iter_error(*raised_error):
                try:
                    next_value = gen.throw(*raised_error)
                except StopIteration:
                    return df.reject(*raised_error)
                except:
                    return df.reject(*sys.exc_info())
                _call_next_or_set_result(next_value)

            # Start and resolve loop.
            try:
                f = next(gen)
            except StopIteration:
                df.resolve(None)
                return df.promise
            _call_next_or_set_result(f)

            return df.promise

        return wrapper
    return decorator
