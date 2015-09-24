# -*- coding: utf-8 -*-

from . import wx_compat  # noqa

import webbrowser
import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl

from ..common.i18n import N_
from .base_view import BaseView
from ..common.path import resource_filename


class AboutBajooWindow(wx.Frame):
    GOOGLE_ICON = None
    FACEBOOK_ICON = None
    TWITTER_ICON = None

    def __init__(self):
        window_style = \
            wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER
        wx.Frame.__init__(
            self, parent=None, title=N_('About Bajoo'), style=window_style)

        icon_path = resource_filename('assets/window_icon.png')
        icon = wx.Icon(icon_path)
        self.SetIcon(icon)

        self._init_icons()
        about_panel = wx.Panel(self)
        self._view = AboutBajooView(about_panel)

        self.Bind(wx.EVT_BUTTON, self._on_click_link)

    def _init_icons(self):
        if not AboutBajooWindow.GOOGLE_ICON:
            AboutBajooWindow.GOOGLE_ICON = wx.Image(
                resource_filename('assets/images/google-plus.png')) \
                .ConvertToBitmap()
        if not AboutBajooWindow.FACEBOOK_ICON:
            AboutBajooWindow.FACEBOOK_ICON = wx.Image(
                resource_filename('assets/images/facebook.png')) \
                .ConvertToBitmap()
        if not AboutBajooWindow.TWITTER_ICON:
            AboutBajooWindow.TWITTER_ICON = wx.Image(
                resource_filename('assets/images/twitter.png')) \
                .ConvertToBitmap()

    def notify_lang_change(self):
        self._view.notify_lang_change()

    def _on_click_link(self, event):
        print(event.GetEventObject())
        if event.GetEventObject() == self.FindWindow('btn_google'):
            webbrowser.open(
                'https://plus.google.com/100830559069902551396/about')
        elif event.GetEventObject() == self.FindWindow('btn_twitter'):
            webbrowser.open('https://twitter.com/mybajoo')
        elif event.GetEventObject() == self.FindWindow('btn_facebook'):
            webbrowser.open(
                'https://www.facebook.com/pages/Bajoo/382879575063022')
        else:
            event.Skip()


class AboutBajooView(BaseView):
    def __init__(self, about_panel):
        BaseView.__init__(self, about_panel)
        from ..__version__ import __version__

        self.window.SetBackgroundColour(wx.Colour(255, 255, 255))

        banner_path = resource_filename('assets/images/side_banner.png')
        bmp_bajoo = wx.Image(banner_path).ConvertToBitmap()
        img_view_bajoo = wx.StaticBitmap(about_panel, label=bmp_bajoo)
        lbl_description = wx.StaticText(
            about_panel, name='lbl_description',
            label=N_('Official client for Bajoo online storage service.\n'
                     'Version: ') + __version__)
        lbl_license = wx.StaticText(
            about_panel, name='lbl_license',
            label=N_('This software is distributed under the terms '
                     'of the GPL License. It is freely redistributable.'))
        lbl_source_code = wx.StaticText(
            about_panel, name='lbl_license',
            label=N_('Its source code is'))
        lbl_source_code_link = HyperLinkCtrl(
            about_panel, label=N_('available on GitHub.'),
            URL='https://www.github.com/bajoo/client')
        lbl_trademarks = wx.StaticText(
            about_panel,
            label=N_(u'The terms Bajoo and Linéa are registered trademarks.'))
        lbl_home_page_link = HyperLinkCtrl(
            about_panel, label=N_('www.bajoo.fr'), URL='https://www.bajoo.fr')
        lbl_libraries = wx.StaticText(
            about_panel,
            label=N_('The client Bajoo reuse the following free elements:'))
        lbl_gpg = wx.StaticText(
            about_panel,
            label=N_('* The GPG software, created by XXX, '
                     'available under the GNU GPL license.'))
        btn_google = wx.BitmapButton(
            about_panel, bitmap=AboutBajooWindow.GOOGLE_ICON,
            style=wx.NO_BORDER, name='btn_google')
        btn_google.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        btn_facebook = wx.BitmapButton(
            about_panel, bitmap=AboutBajooWindow.FACEBOOK_ICON,
            style=wx.NO_BORDER, name='btn_facebook')
        btn_facebook.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        btn_twitter = wx.BitmapButton(
            about_panel, bitmap=AboutBajooWindow.TWITTER_ICON,
            style=wx.NO_BORDER, name='btn_twitter')
        btn_twitter.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        # See bug http://trac.wxwidgets.org/ticket/17145
        bg_color = about_panel.GetBackgroundColour()
        lbl_source_code_link.SetBackgroundColour(bg_color)
        lbl_home_page_link.SetBackgroundColour(bg_color)

        libraries_box = wx.BoxSizer(wx.VERTICAL)
        libraries_box.AddMany([lbl_libraries, lbl_gpg])

        source_code_sizer = wx.BoxSizer(wx.HORIZONTAL)
        source_code_sizer.AddMany(
            [lbl_source_code, (lbl_source_code_link, 0, wx.LEFT, 3)])

        text_sizer = self.make_sizer(
            wx.VERTICAL, [
                None, lbl_description, lbl_license, source_code_sizer,
                lbl_trademarks, lbl_home_page_link, libraries_box, None
            ], outside_border=False)
        social_buttons_sizer = self.make_sizer(wx.VERTICAL, [
            None, btn_facebook, btn_twitter, btn_google, None
        ])

        main_sizer = self.make_sizer(wx.HORIZONTAL, [
            img_view_bajoo, text_sizer, social_buttons_sizer
        ], outside_border=False)
        about_panel.SetSizer(main_sizer)
        main_sizer.SetSizeHints(about_panel.GetTopLevelParent())


def main():
    app = wx.App()
    win = AboutBajooWindow()
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
