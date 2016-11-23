# -*- coding: utf-8 -*-

import os
import sys

from ...gtk_process import is_gtk3_process, proxy_factory

# flake8: noqa
from .about_window_wx_view import AboutWindowWxView
from .task_bar_icon_wx_view import TaskBarIconWxView

if is_gtk3_process():
    from .task_bar_icon_gtk_view import TaskBarIconGtkView
    from .task_bar_icon_appindicator_view import TaskBarIconAppIndicatorView
    from .about_window_gtk_view import AboutWindowGtkView
else:
    AboutWindowGtkView = proxy_factory('AboutWindowGtkView', __name__)
    TaskBarIconGtkView = proxy_factory('TaskBarIconGtkView', __name__)
    TaskBarIconAppIndicatorView = proxy_factory('TaskBarIconAppIndicatorView', __name__)


def _get_task_bar_icon_view():
    # Special case for unity desktop
    if (sys.platform not in ["win32", "cygwin", "darwin"] and
            os.environ.get('DESKTOP_SESSION', '').startswith("ubuntu")):
        return TaskBarIconAppIndicatorView
    else:
        return TaskBarIconWxView


# Choices of view implementation
AboutWindowView = AboutWindowWxView
TaskBarIconView = _get_task_bar_icon_view()


__all__ = [
    AboutWindowView,
    TaskBarIconView
]
