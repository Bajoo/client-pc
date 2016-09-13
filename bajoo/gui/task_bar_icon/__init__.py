# -*- coding: utf-8 -*-

import os
import sys

from .base import WindowDestination, ContainerStatus
from .controller import Controller
from .unity_adapter_view import UnityAdapterView

# Compatibility code for calling GTK3 only in the good process.
from ...gtk_process import is_gtk3_process, proxy_factory

if is_gtk3_process():
    from .gtk_view import TaskBarIconView
else:
    TaskBarIconView = proxy_factory('TaskBarIconView', __name__)


def make_task_bar_icon():
    """Create the best suited task bar icon for the window manager.

    Returns:
        Controller: task bar icon controller.
    """
    if sys.platform not in ["win32", "cygwin", "darwin"]:
        desktop_session = os.environ.get("DESKTOP_SESSION")

        if desktop_session and desktop_session.startswith("ubuntu"):
            # special case for Unity desktop
            return Controller(UnityAdapterView)

    return Controller(TaskBarIconView)


__all__ = [make_task_bar_icon, WindowDestination, ContainerStatus]
