# -*- coding: utf-8 -*-

import webbrowser
from ....common.signal import Signal
from ..bug_report_window import BugReportWindow


class Page(object):
    """Enum of Bajoo social network pages."""
    TWITTER = 'TWITTER'
    GPLUS = 'G+'
    FACEBOOK = 'FACEBOOK'


class AboutWindowController(object):
    """Controller of "About Bajoo" Window.

    The window displays a description of Bajoo, list the dependencies, and
    contains web links. It also have an option to "report a bug" (by opening
    the Bug Report window)

    Attributes:
        destroyed (Signal): fired when the window is about to be destroyed.
    """

    def __init__(self, view_factory, app):
        self.view = view_factory(self)
        self.app = app

        self.destroyed = Signal()

    def show(self):
        """Make the window visible and set in in foreground."""
        self.view.show()

    def destroy(self):
        """Close the Window."""
        self.destroyed.fire()
        self.view.destroy()

    def notify_lang_change(self):
        self.view.notify_lang_change()

    def is_in_use(self):
        """Determine if the window is in use.

        The Window is considered in use if it's visible.
        Returns:
            bool: True if visible; false if not.
        """
        return self.view.is_in_use()

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
