# -*- coding: utf-8 -*-

import functools
from . import wx_compat  # noqa

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
