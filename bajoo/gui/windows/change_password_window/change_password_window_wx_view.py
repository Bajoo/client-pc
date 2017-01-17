
import wx

from ....common.i18n import N_
from ...base_view import BaseView
from ...form.change_password_form import ChangePasswordForm
from .change_password_window_base_view import ChangePasswordWindowBaseView


class ChangePasswordWindowWxView(ChangePasswordWindowBaseView, BaseView,
                                 wx.Dialog):

    ID_DESTROY_VIEW = wx.NewId()

    def __init__(self, ctrl, parent):
        ChangePasswordWindowBaseView.__init__(self, ctrl, parent)
        wx.Dialog.__init__(
            self, parent,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)

        BaseView.__init__(self, self)

        self.register_i18n(self, self.SetTitle, N_('Bajoo - Change password'))
        self.form = ChangePasswordForm(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.form, 0, wx.EXPAND)
        self.SetSizer(sizer)
        self.form.GetSizer().SetSizeHints(self)

        self.Bind(ChangePasswordForm.EVT_SUBMIT, self._on_submit)
        self.Bind(wx.EVT_CLOSE, self._on_cancel)
        self.Bind(wx.EVT_BUTTON, self._on_cancel, id=wx.ID_CANCEL)
        self.CenterOnScreen()

    def show(self):
        self.Show()
        self.Raise()

    def show_modal(self):
        """Show the Windows, and block until window is closed.

        Note: this call is blocking.
        """
        result = self.ShowModal()
        if result is self.ID_DESTROY_VIEW:
            self.Destroy()

    def is_in_use(self):
        return self.IsShown()

    def destroy(self):
        if self.IsModal():
            self.EndModal(self.ID_DESTROY_VIEW)
            # NOTE: We can't destroy the window here: we are still in the
            # EventLoop created by ShowModal() (and so, inside the ShowModal()
            # call)
        else:
            self.Destroy()

    def notify_lang_change(self):
        BaseView.notify_lang_change(self)
        self.form.notify_lang_change()

    def show_error(self, message):
        self.form.show_error(message)

    def _on_submit(self, _event):
        data = self.form.get_data()
        old_password = data[u'old_password']
        new_password = data[u'new_password']
        self.controller.change_password_action(old_password, new_password)

    def _on_cancel(self, _event):
        self.controller.send_cancel_action()
