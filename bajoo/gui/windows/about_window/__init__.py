# -*- coding: utf-8 -*-

import functools
from ....gtk_process import is_gtk3_process, proxy_factory
from .about_window_controller import AboutWindowController
from .about_window_wx_view import AboutWindowWxView

if is_gtk3_process():
    from .about_window_gtk_view import AboutWindowGtkView
else:
    AboutWindowGtkView = proxy_factory('AboutWindowGtkView', __name__)


# Choices of view implementation
AboutWindowView = AboutWindowWxView


AboutWindow = functools.partial(AboutWindowController, AboutWindowView)


__all__ = [
    AboutWindow
]
