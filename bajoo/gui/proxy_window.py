# -*- coding: utf-8 -*-

import wx

from ..common.i18n import N_
from .base_view import BaseView
from .form import ProxyForm


class ProxyWindow(wx.Dialog):
    """Small window containing all proxy settings."""

    def __init__(self, parent):
        wx.Dialog.__init__(
            self, parent,
            style=wx.FRAME_FLOAT_ON_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self._view = ProxyWindowView(self)


class ProxyWindowView(BaseView):
    """View of the ProxyWindow"""

    def __init__(self, window):
        BaseView.__init__(self, window)

        self.set_frame_title(N_('Bajoo - Proxy'))

        self._proxy_form = ProxyForm(window)
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
    app = wx.App()  # noqa
    win = ProxyWindow(None)
    if win.ShowModal() == wx.ID_OK:
        print('OK')
    else:
        print('Action canceled')

if __name__ == '__main__':
    main()
