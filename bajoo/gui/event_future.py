# -*- coding: utf-8 -*-

import wx

from ..common.future import Future


class EventFuture(Future):
    """Bind to a wx event and convert it into a Future.

    the Future can be cancelled until the Bind event is emitted.

    Returns:
        Future<wxEvent>: Future with the selected event.
    """
    def __init__(self, evt_handler, event, source=None):
        """Bind a wx event and resolve this future when the event occurs.

        It equivalent to: ``evt_handler.Bind(event, CALLBACK, source)``

        Args:
            evt_handler (wx.EvtHandler): evt_handler who receive the event.
            event: type of the event, of the form wx.EVT_XXX
            source (optional): source when created the event.
        """
        Future.__init__(self)

        self.evt_handler = evt_handler
        self.event = event
        self.source = source

        evt_handler.Bind(event, self._event_handler, source)

    def _event_handler(self, event):
        """Callback of wxEvent"""
        self.set_running_or_notify_cancel()

        # if the event is wx.EVT_WINDOW_DESTROY, the source widget and its
        # bound functions are already deleted.
        if self.event is not wx.EVT_WINDOW_DESTROY:
            self.evt_handler.Unbind(self.event, source=self.source)
        self.set_result(event)

    def cancel(self):
        self.evt_handler.UnBind(self.event, source=self.source,
                                handler=self._event_handler)
        self.cancel()
        self.set_running_or_notify_cancel()
