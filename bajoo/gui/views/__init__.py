# -*- coding: utf-8 -*-

# from ...gtk_process import is_gtk3_process, proxy_factory

from .about_window_wx_view import AboutWindowWxView

# if is_gtk3_process():
#     from .about_window_gtk_view import AboutWindowGtkView
# else:
#     AboutWindowGtkView = proxy_factory('AboutWindowView', __name__)


# Choices of view implementation
AboutWindowView = AboutWindowWxView

__all__ = [
    AboutWindowView
]
