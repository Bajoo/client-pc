# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class CreationShareTab(wx.Panel):
    """
    The share creation tab in the main window,
    which allows user to create a new share.
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = CreationShareView(self)


class CreationShareView(BaseView):
    """View of the creation share screen"""
    def __init__(self, creation_share_screen):
        BaseView.__init__(self, creation_share_screen)
