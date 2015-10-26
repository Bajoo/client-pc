# -*- coding: utf-8 -*-

import sys
from .promise import Promise
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

            def executor(on_fulfilled, on_rejected):
                # Create generator; Initialization phase
                gen = func(*args, **kwargs)

                def _call_next_or_set_result(value):
                    if is_thenable(value):
                        value.then(iter_next, iter_error)
                    else:
                        gen.close()
                        return on_fulfilled(value)

                def iter_next(yielded_value):
                    try:
                        next_value = gen.send(yielded_value)
                    except StopIteration:
                        return on_fulfilled(yielded_value)
                    except:
                        return on_rejected(*sys.exc_info())
                    _call_next_or_set_result(next_value)

                def iter_error(raised_error):
                    try:
                        next_value = gen.throw(raised_error)
                    except StopIteration:
                        return on_rejected(raised_error)
                    except:
                        return on_rejected(*sys.exc_info())
                    _call_next_or_set_result(next_value)

                # Start and resolve loop.
                f = next(gen)
                _call_next_or_set_result(f)

            p = Promise(executor, _name='COROUTINE %s' % func.__name__)
            if safeguard:
                p.safeguard()
            return p

        return wrapper
    return decorator
