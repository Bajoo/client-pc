# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class ListSharesTab(wx.Panel):
    """
    List shares tab in the main window, which displays
    the status of user's all shares.

    User can then go to the share creation screen or share details screen,
    or can delete a share folder.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = ListSharesView(self)


class ListSharesView(BaseView):
    """View of the list shares screen"""
    def __init__(self, list_shares_screen):
        BaseView.__init__(self, list_shares_screen)
