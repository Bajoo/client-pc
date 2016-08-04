# -*- coding: utf-8 -*-
"""Send and receive file and data between processes.

The module offers two complementary methods, `send_data()` and `recv_data()`,
to transmit data over a Connection object.

If one of the arguments contains a file object (with a file descriptor) and
that this object has been wrapped by `wrap_file()`, it's transmitted between
process.
After sending, the file object is owned by the receiver process, and must no
longer by the emitter.
"""

import io
from multiprocessing.reduction import recv_handle, send_handle
import os
import sys

if sys.platform == 'win32':
    import msvcrt


class _FileObject(object):
    """Placeholder for file-like object using a file descriptor."""
    def __init__(self, fileno):
        self.fileno = fileno


def wrap_file(data):
    """Wrap a file before sending it to another process by `sand_data()`."""
    try:
        return _FileObject(data.fileno())
    except (AttributeError, NotImplementedError, io.UnsupportedOperation):
        return data  # Pseudo File-like object. No need to wrap it.


def send_data(connection, pid, task_id, task, args, kwargs):
    """Send a list of object through a Pipe.

    It must be used jointly with `recv_data()`.

    Args:
        connection (Connection): writeable connection used to transfer data.
        pid (int): receiver process pid
        task_id: unique id.
        task (callable): must be picklable
        args (list): args for task
        kwargs (dict): kwargs for task
    """
    msg = [task_id, task, args, kwargs]
    connection.send(msg)

    for item in args:
        if isinstance(item, _FileObject):
            _send_fileno(connection, item.fileno, pid)
    for kw in kwargs:
        if isinstance(kwargs[kw], _FileObject):
            _send_fileno(connection, kwargs[kw].fileno, pid)


def recv_data(connection):
    """Receive data sent via `send_data()`.

    If a file wrapped by `wrap_file()` is received, it will be unwrapped and
    ready to be used.

    Args:
        connection (Connection): readable connection object
    Returns:
        tuple: task_id (int), task (callable), args (tuple), kwargs (dict)
    """
    task_id, task, args, kwargs = connection.recv()

    return [
        task_id,
        task,
        tuple(_recv_item(connection, item) for item in args),
        {k: _recv_item(connection, v) for k, v in kwargs.items()}
    ]


def _send_fileno(connection, fileno, pid):
    """Cross-platform version of send_handle."""
    if sys.platform == 'win32':
        handle = msvcrt.get_osfhandle(fileno)
    else:
        handle = fileno

    return send_handle(connection, handle, pid)


def _recv_item(connection, item):
    """receive one item. If it's a FileObject, unwrap it."""
    if isinstance(item, _FileObject):
        handle = recv_handle(connection)
        if sys.platform == 'win32':
            handle = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        return os.fdopen(handle)
    return item
