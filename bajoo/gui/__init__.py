# -*- coding: utf-8 -*-

from ..gtk_process import is_gtk3_process

if is_gtk3_process():
    # It must be called before any Gtk import.
    import gi
    gi.require_version('Gtk', '3.0')
else:
    from . import wx_compat  # noqa
