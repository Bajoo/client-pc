# -*- coding: utf-8 -*-

import wx
from wx.lib.agw.hyperlink import EVT_HYPERLINK_LEFT, HyperLinkCtrl

from ....common.i18n import N_
from ....common.path import resource_filename
from ...base_view import BaseView
from ...translator import Translator

from .about_window_base_view import AboutWindowBaseView
from .about_window_controller import Page


class AboutWindowWxView(wx.Frame, AboutWindowBaseView, BaseView):
    GOOGLE_ICON = None
    FACEBOOK_ICON = None
    TWITTER_ICON = None

    def __init__(self, ctrl, app_version):
        AboutWindowBaseView.__init__(self, ctrl, app_version)

        window_style = \
            wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER
        wx.Frame.__init__(self, parent=None, style=window_style)

        icon_path = resource_filename('assets/window_icon.png')
        icon = wx.Icon(icon_path)
        self.SetIcon(icon)

        self._init_icons()
        self.about_panel = wx.Panel(self)
        BaseView.__init__(self, self.about_panel)
        self._create_content(self.about_panel)

        self.Bind(wx.EVT_BUTTON, self._on_click_link)

        win = self.FindWindow('contact_dev')
        win.Bind(EVT_HYPERLINK_LEFT, self._bug_report)
        self.Bind(wx.EVT_CLOSE, lambda _evt: self.controller.close_action())
        win.AutoBrowse(False)

    def _create_content(self, about_panel):

        about_panel.SetBackgroundColour(wx.Colour(255, 255, 255))
        bg_color = about_panel.GetBackgroundColour()

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
            label=self.app_version)

        lbl_version_font = wx.Font(10, wx.FONTFAMILY_DEFAULT,
                                   wx.FONTSTYLE_NORMAL, wx.BOLD)
        lbl_version.SetFont(lbl_version_font)

        lbl_license = wx.StaticText(
            about_panel, name='lbl_license',
            label=N_('This software is distributed under the terms '
                     'of the MIT License.'))

        lbl_source_code = wx.StaticText(
            about_panel, name='lbl_source_code',
            label=N_('It is freely redistributable, the source code is '
                     'available'))

        lbl_source_code_link = HyperLinkCtrl(
            about_panel, label=N_('on GitHub.'),
            URL='https://www.github.com/bajoo/client-pc')
        lbl_source_code_link.SetBackgroundColour(bg_color)

        lbl_trademarks = wx.StaticText(
            about_panel,
            label=N_(u'Bajoo is a registered trademark.'))

        lbl_home_page_link = HyperLinkCtrl(
            about_panel, label=N_('www.bajoo.fr'), URL='https://www.bajoo.fr')
        lbl_home_page_link.SetBackgroundColour(bg_color)

        lbl_frequently_asked_url = HyperLinkCtrl(
            about_panel, label=N_('List of frequently asked questions.'),
            URL='https://www.bajoo.fr/partage-de-dossiers')
        lbl_frequently_asked_url.SetBackgroundColour(bg_color)

        lbl_contact_us = wx.StaticText(
            about_panel,
            label=N_('If you have a new question, feel free to '))

        lbl_contact_us_url = HyperLinkCtrl(
            about_panel, label=N_('contact us'),
            URL='https://www.bajoo.fr/contact')
        lbl_contact_us_url.SetBackgroundColour(bg_color)

        lbl_contact_or_url = wx.StaticText(
            about_panel,
            label=N_(' or '))

        lbl_contact_dev_url = HyperLinkCtrl(
            about_panel, label=N_('report a problem.'),
            name='contact_dev')
        lbl_contact_dev_url.SetBackgroundColour(bg_color)

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

        lbl_notify2 = HyperLinkCtrl(
            about_panel, label='notify2',
            URL='https://pypi.python.org/pypi/notify2')
        lbl_notify2.SetBackgroundColour(bg_color)

        lbl_pypiwin32 = HyperLinkCtrl(
            about_panel, label='pypiwin32',
            URL='https://pypi.python.org/pypi/pypiwin32')
        lbl_pypiwin32.SetBackgroundColour(bg_color)

        btn_google = wx.BitmapButton(
            about_panel, bitmap=self.GOOGLE_ICON,
            style=wx.NO_BORDER, name='btn_google')
        btn_google.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        btn_facebook = wx.BitmapButton(
            about_panel, bitmap=self.FACEBOOK_ICON,
            style=wx.NO_BORDER, name='btn_facebook')
        btn_facebook.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        btn_twitter = wx.BitmapButton(
            about_panel, bitmap=self.TWITTER_ICON,
            style=wx.NO_BORDER, name='btn_twitter')
        btn_twitter.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

        libraries_box = wx.BoxSizer(wx.HORIZONTAL)
        libraries_box.AddMany([lbl_wxpython, (lbl_appdirs, 0, wx.LEFT, 6),
                               (lbl_requests, 0, wx.LEFT, 6),
                               (lbl_futures, 0, wx.LEFT, 6),
                               (lbl_python_gnupg, 0, wx.LEFT, 6),
                               (lbl_watchdog, 0, wx.LEFT, 6),
                               (lbl_pysocks, 0, wx.LEFT, 6),
                               (lbl_notify2, 0, wx.LEFT, 6),
                               (lbl_pypiwin32, 0, wx.LEFT, 6)])

        about_panel.source_code_sizer = wx.BoxSizer(wx.HORIZONTAL)
        about_panel.source_code_sizer.AddMany(
            [lbl_source_code, (lbl_source_code_link, 0, wx.LEFT, 3)])

        about_panel.bajoo_trademark_sizer = wx.BoxSizer(wx.HORIZONTAL)
        about_panel.bajoo_trademark_sizer.AddMany([
            lbl_trademarks, (lbl_home_page_link, 0, wx.LEFT, 6)])

        version_sizer = wx.BoxSizer(wx.HORIZONTAL)
        version_sizer.AddMany([lbl_version_title, (lbl_version, 0,
                                                   wx.LEFT, 3,)])

        about_panel.contact_sizer = wx.BoxSizer(wx.HORIZONTAL)
        about_panel.contact_sizer.AddMany([lbl_contact_us,
                                           (lbl_contact_us_url, 0, wx.LEFT, 3),
                                           lbl_contact_or_url,
                                           lbl_contact_dev_url])

        # Add all left-aligned elements
        text_sizer = self.make_sizer(
            wx.VERTICAL, [
                None, lbl_description, version_sizer, None,
                lbl_frequently_asked_url, about_panel.contact_sizer, None,
                lbl_license, about_panel.source_code_sizer, None,
                lbl_libraries, libraries_box, None,
                about_panel.bajoo_trademark_sizer, None
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

        self.register_i18n(about_panel,
                           self.SetTitle,
                           N_('About Bajoo'))

        self.register_many_i18n('SetLabel', {
            lbl_description: N_('Official software for Bajoo online storage '
                                'service.'),
            lbl_version_title: N_('Version: '),
            lbl_license: N_('This software is distributed under the terms of '
                            'the MIT License.'),
            lbl_source_code: N_('It is freely redistributable, the source '
                                'code is available'),
            lbl_source_code_link: N_('on GitHub.'),
            lbl_trademarks: N_(u'Bajoo is a registered trademark.'),
            lbl_home_page_link: N_('www.bajoo.fr'),
            lbl_frequently_asked_url: N_('List of frequently asked '
                                         'questions.'),
            lbl_contact_us: N_('If you have a new question, feel free to'),
            lbl_contact_us_url: N_('contact us'),
            lbl_contact_or_url: N_(' or '),
            lbl_contact_dev_url: N_('report a problem.'),
            lbl_libraries: N_('Bajoo uses the following libraries:')
        })

    def show(self):
        self.about_panel.Layout()
        self.about_panel.contact_sizer.Layout()
        self.about_panel.source_code_sizer.Layout()
        self.about_panel.bajoo_trademark_sizer.Layout()
        self.Show()
        self.Raise()

    def is_in_use(self):
        return self.IsShown()

    @classmethod
    def _init_icons(cls):
        if not AboutWindowWxView.GOOGLE_ICON:
            cls.GOOGLE_ICON = wx.Image(
                resource_filename('assets/images/google-plus.png')) \
                .ConvertToBitmap()
        if not cls.FACEBOOK_ICON:
            cls.FACEBOOK_ICON = wx.Image(
                resource_filename('assets/images/facebook.png')) \
                .ConvertToBitmap()
        if not cls.TWITTER_ICON:
            cls.TWITTER_ICON = wx.Image(
                resource_filename('assets/images/twitter.png')) \
                .ConvertToBitmap()

    def notify_lang_change(self):
        Translator.notify_lang_change(self)

        self.contact_sizer.Layout()
        self.source_code_sizer.Layout()
        self.bajoo_trademark_sizer.Layout()

    def _on_click_link(self, event):
        if event.GetEventObject() == self.FindWindow('btn_google'):
            self.controller.open_webpage_action(Page.GPLUS)
        elif event.GetEventObject() == self.FindWindow('btn_twitter'):
            self.controller.open_webpage_action(Page.TWITTER)
        elif event.GetEventObject() == self.FindWindow('btn_facebook'):
            self.controller.open_webpage_action(Page.FACEBOOK)
        else:
            event.Skip()

    def _bug_report(self, event):
        self.controller.bug_report_action()

    def destroy(self):
        self.Destroy()
