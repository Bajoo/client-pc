# -*- coding: utf-8 -*-

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl, EVT_HYPERLINK_LEFT

from ...common.i18n import N_
from ..base_view import BaseView
from ..proxy_window import ProxyWindow


class HomeScreen(wx.Panel):
    """Home screen, presenting the connection form."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.proxy_settings_link = HyperLinkCtrl(self)

        self._view = HomeScreenView(self)

        self.Bind(EVT_HYPERLINK_LEFT, self._open_proxy_window,
                  self.proxy_settings_link)

    def _open_proxy_window(self, _event):
        pw = ProxyWindow(self)
        pw.ShowModal()


class HomeScreenView(BaseView):

    def __init__(self, home_screen):
        BaseView.__init__(self, home_screen)

        self.set_frame_title(N_('Bajoo'))

        app_name_txt = wx.StaticText(home_screen)
        app_name_txt.SetFont(app_name_txt.GetFont().Scaled(3.5))
        self.register_i18n(app_name_txt.SetLabel, N_('Bajoo'))
        app_subtitle_txt = wx.StaticText(home_screen)
        app_subtitle_txt.SetFont(app_subtitle_txt.GetFont().Scaled(2.5))
        self.register_i18n(app_subtitle_txt.SetLabel,
                           N_('Your online file storage, secure!'))
        home_screen.proxy_settings_link.DoPopup(False)
        home_screen.proxy_settings_link.AutoBrowse(False)
        self.register_i18n(home_screen.proxy_settings_link.SetLabel,
                           N_('proxy settings'))
        lang_label = wx.StaticText(home_screen)
        self.register_i18n(lang_label.SetLabel, N_('Language:'))
        notebook = wx.Notebook(home_screen)
        # TODO: add forms.
        notebook.AddPage(
            wx.StaticText(notebook,
                          label='TODO: insert connect form HERE\n\n\n\n'),
            N_('Connection'))
        notebook.AddPage(
            wx.StaticText(notebook,
                          label='TODO: insert register form HERE\n\n\n\n'),
            N_('Make an account'))

        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        title_sizer.AddStretchSpacer()
        title_sizer.Add(app_name_txt, flag=wx.ALL, border=15)
        title_sizer.AddStretchSpacer()
        title_sizer.Add(app_subtitle_txt, flag=wx.ALL | wx.ALIGN_BOTTOM,
                        border=15)
        title_sizer.AddStretchSpacer()

        settings_sizer = wx.BoxSizer(wx.HORIZONTAL)
        settings_sizer.Add(home_screen.proxy_settings_link,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.AddStretchSpacer()
        settings_sizer.Add(lang_label,
                           flag=wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, border=10)
        settings_sizer.Add(wx.ComboBox(home_screen, value="Auto"))

        right_column = wx.BoxSizer(wx.VERTICAL)
        right_column.AddStretchSpacer()
        right_column.Add(notebook, flag=wx.ALIGN_CENTER)
        right_column.AddStretchSpacer()
        right_column.Add(settings_sizer, flag=wx.EXPAND | wx.ALL, border=15)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bmp = wx.Image('bajoo/assets/images/home_bajoo_mascot.png')\
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
