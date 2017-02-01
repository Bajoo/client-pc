# -*- coding: utf-8 -*-

from functools import partial
from .bug_report_window_controller import BugReportWindowController
from .bug_report_window_wx_view import BugReportWindowWxView


# Choices of view implementation
BugReportWindowView = BugReportWindowWxView


BugReportWindow = partial(BugReportWindowController, BugReportWindowView)


__all__ = [
    BugReportWindow
]
