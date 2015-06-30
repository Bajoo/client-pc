# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class DetailsShareTab(wx.Panel):
    """
    The share details tab in the main window, which display
    name, type & status of a share.

    User can also manage this share's all permissions here.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = DetailsShareView(self)


class DetailsShareView(BaseView):
    """View of the details share screen"""
    def __init__(self, details_share_screen):
        BaseView.__init__(self, details_share_screen)
