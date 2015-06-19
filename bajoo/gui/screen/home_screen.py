# -*- coding: utf-8 -*-

from functools import partial
import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl, EVT_HYPERLINK_LEFT

from ...common.i18n import N_
from ..base_view import BaseView
from ..form import ConnectionForm
from ..proxy_window import ProxyWindow


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
    """

    EVT_CONNECTION_SUBMIT = ConnectionForm.EVT_SUBMIT

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self._view = HomeScreenView(self)

        self.Bind(EVT_HYPERLINK_LEFT, self._open_proxy_window,
                  self.FindWindowByName('proxy_settings_link'))

        self.Bind(ConnectionForm.EVT_SUBMIT, self._on_submitted_form)

    def _on_submitted_form(self, event):
        """Disable all the notebook when a form is submitted."""
        self.FindWindowByName('notebook').Disable()
        event.Skip()

    def reset_form(self, username=None, errors=None):
        """Prepare or reset the form with initial values."""
        self.FindWindowByName('notebook').Enable()
        self._view.get_active_form().enable()
        # TODO: transmit username and error to the form.

    def _open_proxy_window(self, _event):
        pw = ProxyWindow(self)
        pw.ShowModal()


class HomeScreenView(BaseView):

    def __init__(self, home_screen):
        BaseView.__init__(self, home_screen)

        self.set_frame_title(N_('Bajoo'))

        app_name_txt = wx.StaticText(home_screen)
        app_name_txt.SetFont(app_name_txt.GetFont().Scaled(3.5))
        app_subtitle_txt = wx.StaticText(home_screen)
        app_subtitle_txt.SetFont(app_subtitle_txt.GetFont().Scaled(2.5))
        proxy_settings_link = HyperLinkCtrl(home_screen,
                                            name='proxy_settings_link')
        proxy_settings_link.DoPopup(False)
        proxy_settings_link.AutoBrowse(False)
        lang_label = wx.StaticText(home_screen)

        notebook = wx.Notebook(home_screen, name='notebook')

        connection_form = ConnectionForm(notebook, name='connection_form')
        notebook.AddPage(connection_form, '')
        self.register_i18n(partial(notebook.SetPageText, 0), N_('Connection'))
        # TODO: add register forms.
        register_form = wx.StaticText(
            notebook, label='TODO: Insert register form HERE ...\n')
        notebook.AddPage(register_form, '')
        self.register_i18n(partial(notebook.SetPageText, 1),
                           N_('Make an account'))

        self.register_many_i18n('SetLabel', {
            app_name_txt: N_('Bajoo'),
            app_subtitle_txt: N_('Your online file storage, secure!'),
            proxy_settings_link: N_('proxy settings'),
            lang_label: N_('Language:')
        })

        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        title_sizer.AddStretchSpacer()
        title_sizer.Add(app_name_txt, flag=wx.ALL, border=15)
        title_sizer.AddStretchSpacer()
        title_sizer.Add(app_subtitle_txt, flag=wx.ALL | wx.ALIGN_BOTTOM,
                        border=15)
        title_sizer.AddStretchSpacer()

        settings_sizer = wx.BoxSizer(wx.HORIZONTAL)
        settings_sizer.Add(proxy_settings_link,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.AddStretchSpacer()
        settings_sizer.Add(lang_label,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.Add(wx.ComboBox(home_screen, value="Auto", name='lang'))

        right_column = wx.BoxSizer(wx.VERTICAL)
        right_column.AddStretchSpacer()
        right_column.Add(notebook, flag=wx.ALIGN_CENTER)
        right_column.AddStretchSpacer()
        right_column.Add(settings_sizer, flag=wx.EXPAND | wx.ALL, border=15)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bmp = wx.Image('bajoo/assets/images/home_bajoo_mascot.png') \
            .ConvertToBitmap()
        # Compatibility wxPython classic and phoenix
        if 'phoenix' in wx.version():
            kwargs = {'label': bmp}
        else:
            kwargs = {'bitmap': bmp}
        content_sizer.Add(wx.StaticBitmap(home_screen, **kwargs),
                          proportion=1, flag=wx.ALL | wx.CENTER, border=20)
        content_sizer.Add(right_column, proportion=1,
                          flag=wx.EXPAND | wx.CENTER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(title_sizer, flag=wx.EXPAND, border=30)
        main_sizer.Add(content_sizer, proportion=1, flag=wx.EXPAND, border=30)
        home_screen.SetSizer(main_sizer)

    def get_active_form(self):
        """Find and return the active form."""
        return self.window.FindWindowByName('notebook').GetCurrentPage()


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
