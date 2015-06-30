# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class GeneralSettingsTab(wx.Panel):
    """
    General settings tab in the main window, which allows user to:
    * enable/disable start Bajoo on system startup
    * enable/disable notifications
    * change application language
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = GeneralSettingsView(self)


class GeneralSettingsView(BaseView):
    """View of the general settings screen"""

    def __init__(self, general_settings_screen):
        BaseView.__init__(self, general_settings_screen)
