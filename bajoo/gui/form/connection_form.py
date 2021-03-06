# -*- coding: utf-8 -*-

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl
from wx.lib.newevent import NewCommandEvent

from ...common import config
from ...common.i18n import N_
from ..base_view import BaseView
from ..validator import BaseValidator, NotEmptyValidator, EmailValidator
from . import BaseForm


class ConnectionForm(BaseForm):
    """Connection Form to access user account.

    This form contains two fields:
    * username (wx.TextCtrl)
    * password (wx.TextCtrl)

    When submitted, the form post an event ``ConnectionForm.SubmitEvent``
    containing the properties 'username' and 'password'.
    """

    SubmitEvent, EVT_SUBMIT = NewCommandEvent()

    fields = ['username', 'password']

    def __init__(self, parent, **kwargs):
        BaseForm.__init__(self, parent, auto_disable=True, **kwargs)
        self._view = ConnectionFormView(self)
        self._view.create_children()
        self._view.create_layout()

        self.validators = [
            self.FindWindow('messages'),
            self.FindWindow('username_error'),
            self.FindWindow('password_error')
        ]

        self.Bind(wx.EVT_BUTTON, self.submit, self.FindWindow('submit'))
        self.Bind(wx.EVT_TEXT_ENTER, self.submit, self.FindWindow('username'))
        self.Bind(wx.EVT_TEXT_ENTER, self.submit, self.FindWindow('password'))

    def set_data(self, username=None, errors=None):
        """Initialize the form and set default data."""
        BaseForm.set_data(self, password='', username=username or '')
        if errors:
            self._view.display_message(errors)

    def notify_lang_change(self):
        BaseForm.notify_lang_change(self)
        self._view.notify_lang_change()


class ConnectionFormView(BaseView):
    """View of the ConnectionForm"""

    def create_children(self):
        """Create all named children of proxy form."""

        BaseValidator(self.window, hide_if_valid=True, name='messages')
        username_txt = wx.TextCtrl(self.window, name='username',
                                   style=wx.TE_PROCESS_ENTER)
        EmailValidator(self.window, name='username_error',
                       target=username_txt, hide_if_valid=True)
        password_txt = wx.TextCtrl(self.window, name='password',
                                   style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        NotEmptyValidator(self.window, name='password_error',
                          target=password_txt, hide_if_valid=True)

        submit_btn = wx.Button(self.window, name='submit')
        submit_btn.SetDefault()

        str20 = '123456789ABCDEF01234'
        size = username_txt.GetSizeFromTextSize(
            username_txt.GetTextExtent(str20))
        username_txt.SetMinSize(size)
        password_txt.SetMinSize(size)

        self.register_i18n(username_txt,
                           username_txt.SetHint,
                           N_('Username (email)'))
        self.register_i18n(password_txt,
                           password_txt.SetHint,
                           N_('Password'))
        self.register_i18n(submit_btn,
                           submit_btn.SetLabel,
                           N_('Connection'))

    def create_layout(self):
        """Create appropriate layout and static text for form."""

        # forgotten_password
        forgotten_password_url = '/'.join([
            config.get('identity_api_url'), 'user', 'password-forgotten'])
        forgotten_password_link = HyperLinkCtrl(
            self.window, URL=forgotten_password_url)
        self.register_i18n(forgotten_password_link,
                           forgotten_password_link.SetLabel,
                           N_('Forgot password?'))
        forgotten_password_link.DoPopup(False)

        # See bug http://trac.wxwidgets.org/ticket/17145
        forgotten_password_link.SetBackgroundColour(wx.Colour(255, 255, 255))

        sizer = self.make_sizer(wx.VERTICAL, [
            self.window.FindWindow('messages'),
            self.window.FindWindow('username'),
            self.window.FindWindow('username_error'),
            self.window.FindWindow('password'),
            self.window.FindWindow('password_error'),
            None,
            forgotten_password_link,
            self.window.FindWindow('submit')
        ], flag=wx.EXPAND)
        self.window.SetSizer(sizer)

    def display_message(self, message):
        """Display a message on top of the form."""
        message_text = self.window.FindWindow('messages')
        message_text.set_msg(message)
        self.window.Layout()
        self.window.GetTopLevelParent().Layout()


def main():
    app = wx.App()
    win = wx.Frame(None, title='Connection form')
    app.SetTopWindow(win)

    def _form_submit(event):
        print('Form submitted:')
        print('username = "%s"' % event.username)
        print('password = "%s"' % event.password)

    form = ConnectionForm(win)
    form.set_data()
    win.Bind(ConnectionForm.EVT_SUBMIT, _form_submit)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(form, proportion=1, flag=wx.ALL | wx.EXPAND, border=15)
    win.SetSizer(sizer)
    sizer.SetSizeHints(win)
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
