# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView


_logger = logging.getLogger(__name__)


class GeneralSettingsTab(wx.Panel):
    """
    General settings tab in the main window, which allows user to:
    * enable/disable start Bajoo on system startup
    * enable/disable tray icon
    * enable/disable notifications
    * change application language
    """

    ConfigRequest, EVT_CONFIG_REQUEST = NewCommandEvent()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = GeneralSettingsView(self)

    def Show(self, show=True):
        wx.PostEvent(self, self.ConfigRequest(self.GetId()))

    def load_config(self, config):
        _logger.debug(config)


class GeneralSettingsView(BaseView):
    """View of the general settings screen"""

    def __init__(self, general_settings_screen):
        BaseView.__init__(self, general_settings_screen)

        # chk_launch_at_startup
        chk_launch_at_startup = wx.CheckBox(
            general_settings_screen, name='chk_launch_at_startup')

        # chk_tray_icon
        chk_tray_icon = wx.CheckBox(
            general_settings_screen, name='chk_tray_icon')

        # chk_notifications
        chk_notifications = wx.CheckBox(
            general_settings_screen, name='chk_notifications')

        # cmb_language
        cmb_language = wx.ComboBox(
            general_settings_screen, style=wx.CB_READONLY, name='cmb_language')

        # Options box
        options_box = wx.StaticBox(general_settings_screen)
        options_box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        options_box_sizer_inside = self.make_sizer(
            wx.VERTICAL,
            [chk_launch_at_startup, chk_tray_icon, chk_notifications])
        options_box_sizer.Add(options_box_sizer_inside)

        # Language box
        language_box = wx.StaticBox(general_settings_screen)
        language_box_sizer = wx.StaticBoxSizer(language_box, wx.VERTICAL)
        language_box_sizer.Add(cmb_language, 0,
                               wx.EXPAND | wx.ALL, 10)

        buttons_box = self.create_settings_button_box(
            general_settings_screen)

        # Main sizer
        main_sizer = self.make_sizer(
            wx.VERTICAL,
            [options_box_sizer, language_box_sizer, None, buttons_box])

        general_settings_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            chk_launch_at_startup: N_("Launch Bajoo at system startup"),
            chk_tray_icon: N_("Activate status icon and the contextual menu"),
            chk_notifications: N_("Display a notification when finish "
                                  "downloading file modifications"),
            language_box: N_("Language")
        })


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('General Setttings'))
    app.SetTopWindow(win)

    tab = GeneralSettingsTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
