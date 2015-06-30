# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class GeneralSettingsTab(wx.Panel):
    """
    General settings tab in the main window, which allows user to:
    * enable/disable start Bajoo on system startup
    * enable/disable tray icon
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

        # chk_launch_at_startup
        chk_launch_at_startup = wx.CheckBox(
            general_settings_screen, wx.ID_ANY,
            N_("Launch Bajoo at system startup"),
            name='chk_launch_at_startup')

        # chk_tray_icon
        chk_tray_icon = wx.CheckBox(
            general_settings_screen, wx.ID_ANY,
            N_("Activate status icon and the contextual menu"),
            name='chk_tray_icon')

        # chk_notifications
        chk_notifications = wx.CheckBox(
            general_settings_screen, wx.ID_ANY,
            N_("Display a notification when finish "
               "downloading file modifications"),
            name='chk_notifications')

        # cmb_language
        cmb_language = wx.ComboBox(
            general_settings_screen, wx.ID_ANY,
            style=wx.CB_READONLY,
            name='cmb_language')

        # Options box
        options_box = wx.StaticBox(general_settings_screen, wx.ID_ANY)
        options_box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        options_box_sizer_inside = self.make_sizer(
            wx.VERTICAL,
            [chk_launch_at_startup, chk_tray_icon, chk_notifications])
        options_box_sizer.Add(options_box_sizer_inside)

        # Language box
        language_box = wx.StaticBox(general_settings_screen, wx.ID_ANY,
                                    N_("Language"))
        language_box_sizer = wx.StaticBoxSizer(language_box, wx.VERTICAL)
        language_box_sizer.Add(cmb_language, 0,
                               wx.EXPAND | wx.ALL, 10)

        buttons_box = self.create_settings_button_box(
            general_settings_screen)

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(options_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.Add(language_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.AddStretchSpacer(1)
        main_sizer.Add(buttons_box, 0,
                       wx.EXPAND | wx.ALL, 10)

        general_settings_screen.SetSizer(main_sizer)


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
