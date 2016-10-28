# -*- coding: utf-8 -*-

import functools
from . import wx_compat  # noqa

from .controllers import AboutWindowController
from .views import AboutWindowView


AboutWindow = functools.partial(AboutWindowController, AboutWindowView)

__all__ = [
    AboutWindow
]
