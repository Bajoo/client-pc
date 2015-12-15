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
        wx.Frame.__init__(self, parent=None, style=window_style)

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

        # See bug http://trac.wxwidgets.org/ticket/17145
        bg_color = about_panel.GetBackgroundColour()

        self.window.SetBackgroundColour(wx.Colour(255, 255, 255))

        title_font = wx.Font(
            28, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_BOLD, False)

        banner_path = resource_filename('assets/images/side_banner.png')
        bmp_bajoo = wx.Image(banner_path).ConvertToBitmap()
        img_view_bajoo = wx.StaticBitmap(about_panel, label=bmp_bajoo)

        lbl_title = wx.StaticText(about_panel, label='Bajoo 2')
        lbl_title.SetFont(title_font)

        lbl_description = wx.StaticText(
            about_panel, name='lbl_description',
            label=N_('Official software for Bajoo online storage service.'))

        lbl_version_title = wx.StaticText(
            about_panel, name='lbl_version_title',
            label=N_('Version: '))

        lbl_version = wx.StaticText(
            about_panel, name='lbl_version',
            label=__version__)

        lbl_version_font = wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                   wx.FONTSTYLE_NORMAL, wx.BOLD)
        lbl_version.SetFont(lbl_version_font)

        lbl_license = wx.StaticText(
            about_panel, name='lbl_license',
            label=N_('This software is distributed under the terms '
                     'of the MIT License.'))

        lbl_source_code = wx.StaticText(
            about_panel, name='lbl_license',
            label=N_('It is freely redistributable, the source code is '
                     'available'))

        lbl_source_code_link = HyperLinkCtrl(
            about_panel, label=N_('on GitHub.'),
            URL='https://www.github.com/bajoo/client')
        lbl_source_code_link.SetBackgroundColour(bg_color)

        lbl_trademarks = wx.StaticText(
            about_panel,
            label=N_(u'Bajoo and Linéa are registered trademarks.'))

        lbl_home_page_link = HyperLinkCtrl(
            about_panel, label=N_('www.bajoo.fr'), URL='https://www.bajoo.fr')
        lbl_home_page_link.SetBackgroundColour(bg_color)

        lbl_frequently_asked_url = HyperLinkCtrl(
            about_panel, label=N_('List of frequently asked questions.'),
            URL='https://www.bajoo.fr/partage-de-dossiers')
        lbl_frequently_asked_url.SetBackgroundColour(bg_color)

        lbl_contact_us = wx.StaticText(
            about_panel,
            label=N_('If you have a new question, feel free to'))

        lbl_contact_us_url = HyperLinkCtrl(
            about_panel, label=N_('contact us.'),
            URL='https://www.bajoo.fr/contact')
        lbl_contact_us_url.SetBackgroundColour(bg_color)

        lbl_libraries = wx.StaticText(
            about_panel,
            label=N_('Bajoo uses the following libraries:'))

        lbl_wxpython = HyperLinkCtrl(
            about_panel, label='wxpython', URL='http://www.wxpython.org')
        lbl_wxpython.SetBackgroundColour(bg_color)

        lbl_appdirs = HyperLinkCtrl(
            about_panel, label='appdirs',
            URL='https://pypi.python.org/pypi/appdirs')
        lbl_appdirs.SetBackgroundColour(bg_color)

        lbl_requests = HyperLinkCtrl(
            about_panel, label='requests',
            URL='http://python-requests.org')
        lbl_requests.SetBackgroundColour(bg_color)

        lbl_futures = HyperLinkCtrl(
            about_panel, label='futures',
            URL='https://pypi.python.org/pypi/futures')
        lbl_futures.SetBackgroundColour(bg_color)

        lbl_python_gnupg = HyperLinkCtrl(
            about_panel, label='python-gnupg',
            URL='https://pypi.python.org/pypi/gnupg')
        lbl_python_gnupg.SetBackgroundColour(bg_color)

        lbl_watchdog = HyperLinkCtrl(
            about_panel, label='watchdog',
            URL='https://pypi.python.org/pypi/watchdog')
        lbl_watchdog.SetBackgroundColour(bg_color)

        lbl_pysocks = HyperLinkCtrl(
            about_panel, label='pysocks',
            URL='https://pypi.python.org/pypi/PySocks')
        lbl_pysocks.SetBackgroundColour(bg_color)

        lbl_psutil = HyperLinkCtrl(
            about_panel, label='psutil',
            URL='https://pypi.python.org/pypi/psutil')
        lbl_psutil.SetBackgroundColour(bg_color)

        lbl_notify2 = HyperLinkCtrl(
            about_panel, label='notify2',
            URL='https://pypi.python.org/pypi/notify2')
        lbl_notify2.SetBackgroundColour(bg_color)

        lbl_pypiwin32 = HyperLinkCtrl(
            about_panel, label='pypiwin32',
            URL='https://pypi.python.org/pypi/pypiwin32')
        lbl_pypiwin32.SetBackgroundColour(bg_color)

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

        libraries_box = wx.BoxSizer(wx.HORIZONTAL)
        libraries_box.AddMany([lbl_wxpython, (lbl_appdirs, 0, wx.LEFT, 6),
                               (lbl_requests, 0, wx.LEFT, 6),
                               (lbl_futures, 0, wx.LEFT, 6),
                               (lbl_python_gnupg, 0, wx.LEFT, 6),
                               (lbl_watchdog, 0, wx.LEFT, 6),
                               (lbl_pysocks, 0, wx.LEFT, 6),
                               (lbl_psutil, 0, wx.LEFT, 6),
                               (lbl_notify2, 0, wx.LEFT, 6),
                               (lbl_pypiwin32, 0, wx.LEFT, 6)])

        source_code_sizer = wx.BoxSizer(wx.HORIZONTAL)
        source_code_sizer.AddMany(
            [lbl_source_code, (lbl_source_code_link, 0, wx.LEFT, 3)])

        bajoo_trademark_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bajoo_trademark_sizer.AddMany([lbl_trademarks, (lbl_home_page_link, 0,
                                                        wx.LEFT, 6)])

        version_sizer = wx.BoxSizer(wx.HORIZONTAL)
        version_sizer.AddMany([lbl_version_title, (lbl_version, 0,
                                                   wx.LEFT, 3,)])

        contact_sizer = wx.BoxSizer(wx.HORIZONTAL)
        contact_sizer.AddMany([lbl_contact_us, (lbl_contact_us_url, 0,
                                                wx.LEFT, 3,)])

        # Add all left-aligned elements
        text_sizer = self.make_sizer(
            wx.VERTICAL, [
                None, lbl_description, version_sizer, None,
                lbl_frequently_asked_url, contact_sizer, None,
                lbl_license, source_code_sizer, None,
                lbl_libraries, libraries_box, None,
                bajoo_trademark_sizer, None
            ], outside_border=False, border=5)

        # Insert the title at the top of the page
        # with a top space of 15 and center alignment
        text_sizer.Insert(
            0, lbl_title,
            flag=wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, border=15)

        social_buttons_sizer = self.make_sizer(wx.VERTICAL, [
            None, btn_facebook, btn_twitter, btn_google, None
        ])

        main_sizer = self.make_sizer(wx.HORIZONTAL, [
            img_view_bajoo, text_sizer, social_buttons_sizer
        ], outside_border=False, border=25)
        about_panel.SetSizer(main_sizer)
        main_sizer.SetSizeHints(about_panel.GetTopLevelParent())

        self.register_i18n(about_panel.GetTopLevelParent().SetTitle,
                           N_('About Bajoo'))


def main():
    app = wx.App()
    win = AboutBajooWindow()
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
