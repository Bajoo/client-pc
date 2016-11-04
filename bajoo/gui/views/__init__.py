# -*- coding: utf-8 -*-

import os
import sys

from ...gtk_process import is_gtk3_process, proxy_factory

# flake8: noqa
from .about_window_wx_view import AboutWindowWxView
from .task_bar_icon_wx_view import TaskBarIconWxView
from .task_bar_icon_unity_adapter_view import TaskBarIconUnityAdapterView

if is_gtk3_process():
    from .task_bar_icon_gtk_view import TaskBarIconGtkView
    from .about_window_gtk_view import AboutWindowGtkView
else:
    AboutWindowGtkView = proxy_factory('AboutWindowView', __name__)
    TaskBarIconGtkView = proxy_factory('TaskBarIconView', __name__)


# Choices of view implementation
AboutWindowView = AboutWindowWxView


TaskBarIconView = TaskBarIconWxView
if (sys.platform not in ["win32", "cygwin", "darwin"] and
        os.environ.get('DESKTOP_SESSION', '').startswith("ubuntu")):
    # special case for Unity desktop
    TaskBarIconView = TaskBarIconUnityAdapterView


__all__ = [
    AboutWindowView,
    TaskBarIconView
]
