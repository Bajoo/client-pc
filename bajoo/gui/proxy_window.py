# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewEvent

from ..common.i18n import N_
from .base_view import BaseView
from .form import ProxyForm


ProxyFormRequest, EVT_PROXY_FORM = NewEvent()
"""Event emitted when the user wants to change its proxy settings.

Attributes:
    data (dict): All proxy settings. See ``ProxyForm``.
"""


class ProxyWindow(wx.Dialog):
    """Small window containing all proxy settings.

    This window is a modal window: it's expected to be displayed with
    ``ShowModal()``.

    If the user change it's proxy settings by validating the form, an event
    ``ProxyEvent`` is raised with the wx.App as destination.

    It contains a child named 'proxy_form', instance of ProxyForm.
    """

    def __init__(self, parent):
        wx.Dialog.__init__(
            self, parent,
            style=wx.FRAME_FLOAT_ON_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self._view = ProxyWindowView(self)

        self.Bind(wx.EVT_BUTTON, self._on_submit)

    def _on_submit(self, event):
        if event.GetId() == wx.ID_OK:
            data = self.FindWindowByName('proxy_form').get_data()
            proxy_event = ProxyFormRequest(data=data)
            wx.PostEvent(wx.GetApp(), proxy_event)
        event.Skip()


class ProxyWindowView(BaseView):
    """View of the ProxyWindow"""

    def __init__(self, window):
        BaseView.__init__(self, window)

        self.set_frame_title(N_('Bajoo - Proxy'))

        self._proxy_form = ProxyForm(window, name='proxy_form')
        self._apply_btn = wx.Button(window, id=wx.ID_OK)
        self._cancel_btn = wx.Button(window, id=wx.ID_CANCEL)

        self.register_i18n(self._cancel_btn.SetLabel, N_('Cancel'))
        self.register_i18n(self._apply_btn.SetLabel, N_('OK'))

        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self._cancel_btn)
        btn_sizer.AddButton(self._apply_btn)
        btn_sizer.Realize()
        sizer = self.make_sizer(wx.VERTICAL, [self._proxy_form, btn_sizer],
                                flag=wx.EXPAND)
        sizer.SetSizeHints(window)
        window.SetSizer(sizer)


def main():
    app = wx.App()
    win = ProxyWindow(None)

    def _proxy_event(event):
        print('Proxy event received:')
        print(event.data)
        win.Destroy()  # Explicitly stop the MainLoop()

    app.Bind(EVT_PROXY_FORM, _proxy_event)

    if win.ShowModal() == wx.ID_OK:
        print('OK')
    else:
        print('Action canceled')
    app.MainLoop()

if __name__ == '__main__':
    main()
