# -*- coding: utf-8 -*-

import webbrowser
from ..base_window_controller import BaseWindowController
from ..bug_report_window import BugReportWindow


class Page(object):
    """Enum of Bajoo social network pages."""
    TWITTER = 'TWITTER'
    GPLUS = 'G+'
    FACEBOOK = 'FACEBOOK'


class AboutWindowController(BaseWindowController):
    """Controller of "About Bajoo" Window.

    The window displays a description of Bajoo, list the dependencies, and
    contains web links. It also have an option to "report a bug" (by opening
    the Bug Report window)
    """

    def __init__(self, view_factory, app):
        BaseWindowController.__init__(self, view_factory, app)
        self.view.app_version = app.version

    def open_webpage_action(self, target_page):
        """Open one of the social network pages of Bajoo

        Args:
            target_page (Page): one of the pages listed in Page enum.
        """
        url_mapping = {
            Page.GPLUS: 'https://plus.google.com/100830559069902551396/about',
            Page.TWITTER: 'https://twitter.com/mybajoo',
            Page.FACEBOOK:
                'https://www.facebook.com/pages/Bajoo/382879575063022',
        }
        webbrowser.open(url_mapping[target_page])

    def bug_report_action(self):
        """Open the bug report window."""
        bug_dialog = BugReportWindow(self.app)
        bug_dialog.ShowModal()

    def close_action(self):
        """The user wants to close the window."""
        self.destroy()
