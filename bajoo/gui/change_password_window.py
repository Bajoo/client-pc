# -*- coding: utf-8 -*-

import logging

import wx

from ..common.i18n import N_
from .form.change_password_form import ChangePasswordForm
from .translator import Translator


_logger = logging.getLogger(__name__)


class ChangePasswordWindow(wx.Dialog, Translator):
    """
    Allows user to change password.
    """

    EVT_CHANGE_PASSWORD_SUBMIT = ChangePasswordForm.EVT_SUBMIT

    def __init__(self, parent):
        wx.Dialog.__init__(
            self, parent,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        Translator.__init__(self)
        self.register_i18n(self, self.SetTitle, N_('Bajoo - Change password'))
        self.form = ChangePasswordForm(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.form, 0, wx.EXPAND)
        self.SetSizer(sizer)
        self.form.GetSizer().SetSizeHints(self)

        self.Bind(ChangePasswordForm.EVT_SUBMIT, self._on_submit)
        self.CenterOnScreen()

    def _on_submit(self, event):
        event.data = self.form.get_data()
        event.Skip()

    def show_error(self, message):
        self.form.show_error(message)

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self.form.notify_lang_change()


def main():
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    app = wx.App()
    window = ChangePasswordWindow(None)

    def _on_change_password_request(event):
        print('Change password request received:')
        print(event.data)

    app.Bind(ChangePasswordWindow.EVT_CHANGE_PASSWORD_SUBMIT,
             _on_change_password_request)

    window.ShowModal()
    window.Destroy()

    app.MainLoop()


if __name__ == '__main__':
    main()
