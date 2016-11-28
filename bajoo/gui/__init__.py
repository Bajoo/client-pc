# -*- coding: utf-8 -*-

import functools
from ..gtk_process import is_gtk3_process

if is_gtk3_process():
    # It must be called before any Gtk import.
    import gi
    gi.require_version('Gtk', '3.0')
else:
    from . import wx_compat  # noqa

# flake8: noqa
from .controllers import AboutWindowController
from .controllers import TaskBarIconController
from .views import AboutWindowView
from .views import TaskBarIconView


AboutWindow = functools.partial(AboutWindowController, AboutWindowView)
TaskBarIcon = functools.partial(TaskBarIconController, TaskBarIconView)

__all__ = [
    AboutWindow,
    TaskBarIcon
]
