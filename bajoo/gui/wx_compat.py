# -*- coding: utf-8 -*-
"""Patch wxPython to keep a better compatibility across different versions.

The phoenix version of wx.Python is the reference. When a feature have been
modified or is missing in the classic version, the 'classic' lib is patched to
look like the 'phoenix' one.
"""

import wx


# In 'classic' version, wx.Window.FindWindowByName() will search a child of the
# window. In 'phoenix' version, the same method will search amongst all
# windows, even not child of the caller window.
# wx.Window.FindWindow exists only in wxPython phoenix, and has the expected
# behavior (search only the children of the caller).
if not hasattr(wx.Window, 'FindWindow'):
    wx.Window.FindWindow = wx.Window.FindWindowByName


# Renamed function
if 'phoenix' not in wx.version():
    wx.IsMainThread = wx.Thread_IsMain


# Renamed named argument 'bitmap' to 'label' on wx.StaticBitmap.__init__()
if 'phoenix' not in wx.version():
    _static_bitmap_init = wx.StaticBitmap.__init__

    def static_bitmap_init(self, *args, **kwargs):
        if 'label' in kwargs:
            kwargs['bitmap'] = kwargs['label']
            del kwargs['label']
        return _static_bitmap_init(self, *args, **kwargs)

    wx.StaticBitmap.__init__ = static_bitmap_init


# GetSizeFromTextSize exists only since version 2.9
# This will set an approximated function if needed.
# The function only compute width by adding a space of margin of each side.
# The height is left by default (-1).
if not hasattr(wx.Control, 'GetSizeFromTextSize'):

    def get_size_from_text_size(self, size):
        margin = self.GetTextExtent('  ')
        width = size[0] + margin[0]
        return width, -1

    wx.Control.GetSizeFromTextSize = get_size_from_text_size
