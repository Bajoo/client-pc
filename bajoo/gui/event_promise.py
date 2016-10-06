# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewEvent

from ..promise import Promise, CancelledError


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


def ensure_gui_thread(safeguard=False):
    """Ensure the function will always be called in the GUI thread.

    This decorator will execute the function only in the GUI thread.
    If we are not in the right thread, it will delay the execution (using
    wx.PostEvent).

    Args:
        safeguard (boolean): if True, use `Promise.safeguard()` on the
            resulting promise.
    Returns:
        Promise: a Promise fulfilled with the return value of the function
            decorated. If the function raise an exception, the promise is
            rejected.
    """

    def decorator(f):
        RunEvent, EVT_RUN = NewEvent()
        handler = wx.EvtHandler()

        def wrapper(*args, **kwargs):
            if wx.IsMainThread():
                try:
                    p = Promise.resolve(f(*args, **kwargs))
                except BaseException as error:
                    p = Promise.reject(error)
            else:
                p = EventPromise(handler, EVT_RUN)
                p = p.then(lambda _evt: f(*args, **kwargs))
                wx.PostEvent(handler, RunEvent())
            if safeguard:
                p.safeguard()
            return p
        return wrapper
    return decorator
