# -*- coding: utf-8 -*-

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
        self._init_icons()
        about_panel = wx.Panel(self)
        self._view = AboutBajooView(about_panel)

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


class AboutBajooView(BaseView):
    def __init__(self, about_panel):
        BaseView.__init__(self, about_panel)
        from ..__version__ import __version__

        bmp_bajoo = wx.Image(
            resource_filename('assets/images/home_bajoo_mascot.png')) \
            .ConvertToBitmap()
        img_view_bajoo = wx.StaticBitmap(about_panel, bitmap=bmp_bajoo)
        lbl_bajoo2 = wx.StaticText(
            about_panel, label='Bajoo 2')
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
            style=wx.NO_BORDER)
        btn_google.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        btn_facebook = wx.BitmapButton(
            about_panel, bitmap=AboutBajooWindow.FACEBOOK_ICON,
            style=wx.NO_BORDER)
        btn_facebook.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        btn_twitter = wx.BitmapButton(
            about_panel, bitmap=AboutBajooWindow.TWITTER_ICON,
            style=wx.NO_BORDER)
        btn_twitter.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        libraries_box = wx.BoxSizer(wx.VERTICAL)
        libraries_box.AddMany([lbl_libraries, lbl_gpg])

        source_code_sizer = wx.BoxSizer(wx.HORIZONTAL)
        source_code_sizer.AddMany(
            [lbl_source_code, (lbl_source_code_link, 0, wx.LEFT, 3)])

        text_sizer = self.make_sizer(
            wx.VERTICAL, [
                lbl_bajoo2, lbl_description, lbl_license, source_code_sizer,
                lbl_trademarks, lbl_home_page_link, libraries_box],
            outside_border=False)
        social_buttons_sizer = self.make_sizer(
            wx.VERTICAL, [None, btn_facebook, btn_twitter, btn_google, None],
            outside_border=False)

        main_sizer = self.make_sizer(
            wx.HORIZONTAL, [img_view_bajoo, text_sizer, social_buttons_sizer])
        about_panel.SetSizer(main_sizer)
        main_sizer.SetSizeHints(about_panel.GetTopLevelParent())


def main():
    app = wx.App()
    win = AboutBajooWindow()
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
