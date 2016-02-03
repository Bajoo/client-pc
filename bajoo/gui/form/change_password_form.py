# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView
from ..form.base_form import BaseForm
from ..validator import NotEmptyValidator

_logger = logging.getLogger(__name__)


class ChangePasswordForm(BaseForm):
    """
    A form which allows users to modify their password.
    It contains three text controls which demands for
    current password, new password and its confirmation.
    """
    SubmitEvent, EVT_SUBMIT = NewCommandEvent()
    fields = ['old_password', 'new_password']

    def __init__(self, parent):
        BaseForm.__init__(self, parent)
        self._view = ChangePasswordView(self)
        self.validators = self._view.get_validators()

        self.Bind(wx.EVT_BUTTON, self._on_submit,
                  self.FindWindowById(wx.ID_APPLY))

    def show_error(self, message):
        lbl_error = self.FindWindow('lbl_error')
        self._view.register_i18n(lbl_error, lbl_error.SetLabel, message)
        lbl_error.Show()

        self.GetTopLevelParent().Layout()

    def hide_error(self):
        lbl_error = self.FindWindow('lbl_error')
        lbl_error.Hide()

    def _on_submit(self, event):
        self.hide_error()
        self.submit(event)

    def notify_lang_change(self):
        BaseForm.notify_lang_change(self)
        self._view.notify_lang_change()


class ChangePasswordView(BaseView):
    """
    The view of the ChangePasswordWindow.
    """

    def __init__(self, change_password_form):
        BaseView.__init__(self, change_password_form)
        text_min_size = (250, -1)

        self._txt_old_password = wx.TextCtrl(
            change_password_form, wx.ID_ANY,
            style=wx.TE_PASSWORD,
            name='old_password')
        self._txt_old_password.SetMinSize(text_min_size)
        self._old_password_error = NotEmptyValidator(
            change_password_form, self._txt_old_password)

        self._txt_new_password = wx.TextCtrl(
            change_password_form, wx.ID_ANY,
            style=wx.TE_PASSWORD,
            name='new_password')
        self._txt_new_password.SetMinSize(text_min_size)
        self._new_password_error = NotEmptyValidator(
            change_password_form, self._txt_new_password)

        self._txt_confirm_new_password = wx.TextCtrl(
            change_password_form, wx.ID_ANY,
            style=wx.TE_PASSWORD,
            name='confirm_new_password')
        self._txt_confirm_new_password.SetMinSize(text_min_size)
        self._confirm_new_password_error = NotEmptyValidator(
            change_password_form, self._txt_confirm_new_password)

        self._btn_ok = wx.Button(change_password_form, wx.ID_APPLY,
                                 name='submit')
        self._btn_cancel = wx.Button(change_password_form, wx.ID_CANCEL)

        buttons_sizer = wx.StdDialogButtonSizer()
        buttons_sizer.Add(self._btn_cancel)
        buttons_sizer.AddStretchSpacer()
        buttons_sizer.Add(self._btn_ok)

        old_password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        old_password_sizer.Add(self._txt_old_password, 1, wx.RIGHT, 5)
        old_password_sizer.Add(self._old_password_error, 0, wx.TOP, 3)

        new_password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        new_password_sizer.Add(self._txt_new_password, 1, wx.RIGHT, 5)
        new_password_sizer.Add(self._new_password_error, 0, wx.TOP, 3)

        confirm_new_password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        confirm_new_password_sizer.Add(
            self._txt_confirm_new_password, 1, wx.RIGHT, 5)
        confirm_new_password_sizer.Add(
            self._confirm_new_password_error, 0, wx.TOP, 3)

        lbl_description = wx.StaticText(
            change_password_form, name='lbl_description')
        lbl_confirmation_email = wx.StaticText(
            change_password_form, name='lbl_confirmation_email')

        lbl_error = wx.StaticText(
            change_password_form, name='lbl_error')
        lbl_error.SetForegroundColour(wx.RED)

        main_sizer = self.make_sizer(
            wx.VERTICAL, [
                lbl_description, lbl_confirmation_email, lbl_error,
                old_password_sizer, new_password_sizer,
                confirm_new_password_sizer, buttons_sizer
            ], flag=wx.EXPAND)
        change_password_form.SetSizer(main_sizer)

        self.register_many_i18n('SetLabel', {
            lbl_description: N_("You are about to change your password.\n"
                                "For this, you need to enter "
                                "your current password, "
                                "and the new password that you want to use."),
            lbl_confirmation_email: N_("Then you will receive "
                                       "a confirmation email.\n"),
            self._btn_cancel: N_("Cancel"),
            self._btn_ok: N_("OK")
        })

        self.register_many_i18n('SetHint', {
            self._txt_old_password: N_('Current password'),
            self._txt_new_password: N_('New password'),
            self._txt_confirm_new_password: N_('Confirm new password'),
        })

    def get_validators(self):
        return [
            self._old_password_error,
            self._new_password_error,
            self._confirm_new_password_error]


def main():
    app = wx.App()
    win = wx.Frame(None, title='Proxy Form')
    app.SetTopWindow(win)

    form = ChangePasswordForm(win)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(form, proportion=1, flag=wx.ALL | wx.EXPAND, border=15)
    win.SetSizer(sizer)
    sizer.SetSizeHints(win)
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
