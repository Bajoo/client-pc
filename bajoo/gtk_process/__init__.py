# -*- coding: utf-8 -*-

from .gtk_process import GtkProcessHandler  # noqa
from .rpc_handler import get_global_rpc_handler


def is_gtk3_process():
    try:
        import gi
        return gi.get_required_version('Gtk') == '3.0'
    except ImportError:
        return False


def remote_call(name, module, *args, **kwargs):
    """Call an object located in a remote process, from its name.

    Args:
        name (str): name of the remote object to call
        module (str): full name of the python module containing the target
            object.
        *args: args transmitted to the callable.
        **kwargs: kwargs transmitted to the callable.

    Returns:
        Any: Whatever the callable returns.
    """
    rpc_handler = get_global_rpc_handler()
    assert rpc_handler is not None
    return rpc_handler.rpc_call_by_name(name, module, *args, **kwargs)


def proxy_factory(class_name, module):
    """Create a factory of proxy specialized over a target class.

    When the factory returned is called, there is a communication with the Gtk
    process. An instance of the target class is created on the gtk side. Then a
    proxy of this instance is returned.

    The proxy objects can be used as a normal object, in a transparent way.

    There is two caveats about proxy use:
    - When a call of remote constructor or method occurs, arguments are wrapped
        into "reverse" proxies (so the remote object can the real instance).
        The wrapping method don't detect attributes of object instances (but
        it detects objects inside lists, dicts and tuples).
    - Cross-references between objects in different processes are not detected
        by the garbage collector. Such object can never be deleted, the
        cross-references are not explicitly deleted.

    Notes:
        The functions returned by the factory must be called after the start of
            the Gtk process.

    Args:
        class_name (str): name of the class that need to be replaced.
        module (str): full name of the python module containing the target
            class.

    Returns:
        Callable: function wrapping the constructor, returning a proxy of the
            new instance.
    """
    def x(*args, **kwargs):
        return remote_call(class_name, module, *args, **kwargs)

    return x
