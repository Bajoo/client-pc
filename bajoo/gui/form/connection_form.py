# -*- coding: utf-8 -*-

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView
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

    def __init__(self, parent, **kwargs):
        BaseForm.__init__(self, parent, auto_disable=True, **kwargs)
        self._view = ConnectionFormView(self)
        self._view.create_children()
        self._view.create_layout()

        # TODO: validate form (empty or bad fields)
        self.Bind(wx.EVT_BUTTON, self.submit, self.FindWindowByName('submit'))


class ConnectionFormView(BaseView):
    """View of the ProxyForm"""

    def create_children(self):
        """Create all named children of proxy form."""

        username_txt = wx.TextCtrl(self.window, name='username')
        password_txt = wx.TextCtrl(self.window, name='password',
                                   style=wx.TE_PASSWORD)

        submit_btn = wx.Button(self.window, name='submit')

        str20 = '123456789ABCDEF01234'
        try:  # wxPython phoenix
            size = username_txt.GetSizefromTextSize(
                username_txt.GetTextExtent(str20))
        except AttributeError:  # wxPython classic
            size = username_txt.GetTextExtent(' %s ' % str20)
            size = (size[0], -1)
        username_txt.SetMinSize(size)
        password_txt.SetMinSize(size)

        self.register_i18n(username_txt.SetHint, N_('Username (email)'))
        self.register_i18n(password_txt.SetHint, N_('Password'))
        self.register_i18n(submit_btn.SetLabel, N_('Connection'))

    def create_layout(self):
        """Create appropriate layout and static text for form."""
        # TODO: set real URL
        forgotten_password_link = HyperLinkCtrl(self.window,
                                                URL='http://www.bajoo.fr')
        self.register_i18n(forgotten_password_link.SetLabel,
                           N_('Password forgotten?'))
        forgotten_password_link.DoPopup(False)

        sizer = self.make_sizer(wx.VERTICAL, [
            self.window.FindWindowByName('username'),
            self.window.FindWindowByName('password'),
            forgotten_password_link,
            self.window.FindWindowByName('submit')
        ])
        self.window.SetSizer(sizer)


def main():
    app = wx.App()
    win = wx.Frame(None, title='Connection form')
    app.SetTopWindow(win)

    def _form_submit(event):
        print('Form submitted:')
        print('username = "%s"' % event.username)
        print('password = "%s"' % event.password)

    form = ConnectionForm(win)
    win.Bind(ConnectionForm.EVT_SUBMIT, _form_submit)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(form, proportion=1, flag=wx.ALL | wx.EXPAND, border=15)
    win.SetSizer(sizer)
    sizer.SetSizeHints(win)
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
