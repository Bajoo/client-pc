# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class NetworkSettingsTab(wx.Panel):
    """
    Network settings tab in the main window, which allows user to:
    * change download/upload bandwidth
    * change proxy settings
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = NetworkSettingsView(self)


class NetworkSettingsView(BaseView):
    """View of the network settings screen"""
    def __init__(self, network_settings_screen):
        BaseView.__init__(self, network_settings_screen)
