# -*- coding: utf-8 -*-

import os
import sys

from .task_bar_icon import TaskBarIcon
from .unity_task_bar_icon_wx_interface import UnityTaskBarIconWxInterface


def make_task_bar_icon(wx_app):
    """Create the best suited task bar icon for the window manager.

    Args:
        wx_app (wx.App)
    Returns:
        AbstractTaskBarIcon
    """
    if sys.platform not in ["win32", "cygwin", "darwin"]:
        desktop_session = os.environ.get("DESKTOP_SESSION")

        if desktop_session and desktop_session.startswith("ubuntu"):
            # special case for Unity desktop
            task_bar_icon = UnityTaskBarIconWxInterface(wx_app)
            task_bar_icon.notify_lang_change()
            return task_bar_icon

    return TaskBarIcon()
