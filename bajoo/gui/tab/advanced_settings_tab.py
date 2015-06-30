# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class AdvancedSettingsTab(wx.Panel):
    """
    Advanced settings tab in the main window, which allows user to:
    * activate/deactivate debug mode
    * send crash reports
    * enable/disable application's auto update
    * enable/disable hidden file synchronization
    """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = AdvancedSettingsView(self)


class AdvancedSettingsView(BaseView):
    """View of the advanced settings screen"""
    def __init__(self, advanced_settings_screen):
        BaseView.__init__(self, advanced_settings_screen)
