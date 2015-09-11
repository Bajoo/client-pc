# -*- coding: utf-8 -*-

from functools import partial

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl, EVT_HYPERLINK_LEFT

from ...common.i18n import N_
from ..base_view import BaseView
from ..form import ConnectionForm, RegisterForm
from ..proxy_window import ProxyWindow
from ..common.language_box import LanguageBox


class HomeScreen(wx.Panel):
    """Home screen, presenting the connection form.

    When one of the two forms are submitted, the corresponding event
    (ConnectionForm.EVT_SUBMIT or RegisterForm.EVT_SUBMIT) is propagated.

    The window has the following named children:
    * notebook (wx.Notebook) contains the two forms.
    * connection_form (ConnectionForm)
    * lang (wx.Choice): the language selection.
    * proxy_settings_link (wx.HyperLinkCtrl)

    Attributes:
        EVT_CONNECTION_SUBMIT (Event Id): event emitted when the connection
            form is submitted.
        EVT_REGISTER_SUBMIT (Event Id): event emitted when the register
            form is submitted.
    """

    EVT_CONNECTION_SUBMIT = ConnectionForm.EVT_SUBMIT
    EVT_REGISTER_SUBMIT = RegisterForm.EVT_SUBMIT

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self._view = HomeScreenView(self)

        self.Bind(EVT_HYPERLINK_LEFT, self._open_proxy_window,
                  self.FindWindow('proxy_settings_link'))

        self.Bind(ConnectionForm.EVT_SUBMIT, self._on_submitted_form)
        self.Bind(RegisterForm.EVT_SUBMIT, self._on_submitted_form)

    def _on_submitted_form(self, event):
        """Disable all the notebook when a form is submitted."""
        self.FindWindow('notebook').Disable()
        event.Skip()

    def reset_form(self, username=None, errors=None):
        """Prepare or reset the form with initial values."""
        self.FindWindow('notebook').Enable()
        self._view.get_active_form().set_data(username, errors)
        self._view.get_active_form().enable()

    def _open_proxy_window(self, _event):
        pw = ProxyWindow(self)
        pw.ShowModal()

    def notify_lang_change(self):
        self._view.notify_lang_change()


class HomeScreenView(BaseView):
    def __init__(self, home_screen):
        BaseView.__init__(self, home_screen)

        self.set_frame_title(N_('Bajoo'))
        self.window.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.window.SetMinSize((350, -1))

        proxy_settings_link = HyperLinkCtrl(home_screen,
                                            name='proxy_settings_link')
        proxy_settings_link.DoPopup(False)
        proxy_settings_link.AutoBrowse(False)
        lang_label = wx.StaticText(home_screen)

        notebook = wx.Notebook(home_screen, name='notebook')

        self._connection_form = ConnectionForm(notebook,
                                               name='connection_form')
        notebook.AddPage(self._connection_form, '')
        self.register_i18n(partial(notebook.SetPageText, 0), N_('Connection'))
        self._register_form = RegisterForm(notebook, name='register_form')
        notebook.AddPage(self._register_form, '')
        self.register_i18n(partial(notebook.SetPageText, 1),
                           N_('Make an account'))

        self.register_many_i18n('SetLabel', {
            proxy_settings_link: N_('proxy settings'),
            lang_label: N_('Language:')
        })

        settings_sizer = wx.BoxSizer(wx.HORIZONTAL)
        settings_sizer.Add(proxy_settings_link,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.AddStretchSpacer()
        settings_sizer.Add(lang_label,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.Add(LanguageBox(home_screen, name='lang'))

        notebook_sizer = wx.BoxSizer(wx.HORIZONTAL)
        notebook_sizer.AddSpacer(15)
        notebook_sizer.Add(notebook, flag=wx.EXPAND, proportion=1)
        notebook_sizer.AddSpacer(15)

        main_sizer = self.make_sizer(wx.VERTICAL, [
            None, notebook_sizer, None, settings_sizer
        ])

        home_screen.SetSizer(main_sizer)

    def get_active_form(self):
        """Find and return the active form."""
        return self.window.FindWindow('notebook').GetCurrentPage()

    def notify_lang_change(self):
        BaseView.notify_lang_change(self)
        self._connection_form.notify_lang_change()
        self._register_form.notify_lang_change()


def main():
    app = wx.App()
    win = wx.Frame(None, title='Home Screen')
    app.SetTopWindow(win)
    s = HomeScreen(win)
    s.GetSizer().SetSizeHints(win)
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
