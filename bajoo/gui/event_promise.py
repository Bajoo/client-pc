# -*- coding: utf-8 -*-

import sys
import wx

from ..promise import Deferred, is_thenable, Promise, CancelledError


class EventPromise(Promise):
    """Bind to a wx event and convert it into a Promise.

    the Promise can be cancelled until the Bind event is emitted.

    Returns:
        Promise<wxEvent>: Promise resolving the event instance.
    """
    def __init__(self, evt_handler, event, source=None):
        """Bind a wx event and resolve this promise when the event occurs.

        It's equivalent to: ``evt_handler.Bind(event, CALLBACK, source)``

        Args:
            evt_handler (wx.EvtHandler): evt_handler who receive the event.
            event: type of the event, of the form wx.EVT_XXX
            source (optional): source when created the event.
        """

        self._fulfill_cb = None
        self._reject_cb = None

        def executor(fulfill_cb, reject_cb):
            self._fulfill_cb = fulfill_cb
            self._reject_cb = reject_cb

        Promise.__init__(self, executor, _name='EVENT')

        self.evt_handler = evt_handler
        self.event = event
        self.source = source

        evt_handler.Bind(event, self._event_handler, source)

    def _inner_print(self):
        # Find the name of the variable referring to the event ID.
        for name in dir(wx):
            if not name.startswith('EVT_'):
                continue
            evt = getattr(wx, name)
            if isinstance(evt, wx.PyEventBinder):
                if evt.typeId == self.event:
                    self._name = 'EVENT %s' % name
                    break

        return Promise._inner_print(self)

    def _event_handler(self, event):
        """Callback of wxEvent"""

        if self.evt_handler is None:
            # Sometimes, the Unbind() is not instant and we caught events that
            # we shouldn't. This is one of these wrong catches.
            event.Skip()
            return

        # if the event is wx.EVT_WINDOW_DESTROY, the source widget and its
        # bound functions are already deleted.
        if self.event is not wx.EVT_WINDOW_DESTROY:
            self.evt_handler.Unbind(self.event, source=self.source)
        self.evt_handler = None
        self._fulfill_cb(event)

    def cancel(self):
        if self.evt_handler:
            self.evt_handler.Unbind(self.event, source=self.source,
                                    handler=self._event_handler)

        with self._condition:
            if self._state == self.PENDING:
                self._reject_cb(CancelledError())
                return True
            else:
                return False


def _wrap_deferred(df, fc, *args, **kwargs):
    """Call a function and use the result to resolve or reject a Deferred.

    Args:
        df (Deferred): deferred to reject or resolve.
        fc (Callable): function that will be called.
        *args: fc arguments
        **kwargs: fc kwargs
    """
    try:
        r = fc(*args, **kwargs)
    except:
        df.reject(*sys.exc_info())
    else:
        if is_thenable(r):
            r.then(df.resolve, df.reject, True)
        else:
            df.resolve(r)


def ensure_gui_thread(safeguard=False):
    """Ensure the function will always be called in the GUI thread.

    This decorator will execute the function only in the GUI thread.
    It will delay the execution, and wrap the result in a Promise.

    Notes:
        If the wrapped function returns a Promise, this Promise will be
        chained, in order to never have nested promises.

    Args:
        safeguard (boolean): if True, use `Promise.safeguard()` on the
            resulting promise.
    Returns:
        Promise: a Promise fulfilled with the return value of the function
            decorated. If the function raise an exception, the promise is
            rejected.
    """

    def decorator(f):
        def wrapper(*args, **kwargs):
            df = Deferred()
            wx.CallAfter(_wrap_deferred, df, f, *args, **kwargs)
            if safeguard:
                df.promise.safeguard()
            return df.promise
        return wrapper
    return decorator
