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

        # btn_ok
        btn_ok = wx.Button(
            general_settings_screen, wx.ID_OK,
            name='btn_ok')

        # btn_cancel
        btn_cancel = wx.Button(
            general_settings_screen, wx.ID_CANCEL,
            name='btn_cancel')

        # btn_apply
        btn_apply = wx.Button(
            general_settings_screen, wx.ID_APPLY,
            name='btn_apply')

        # Options box
        options_box = wx.StaticBox(general_settings_screen, wx.ID_ANY)
        options_box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        options_box_sizer.Add(chk_launch_at_startup, 0,
                              wx.LEFT | wx.TOP, 10)
        options_box_sizer.Add(chk_tray_icon, 0,
                              wx.LEFT | wx.TOP, 10)
        options_box_sizer.Add(chk_notifications, 0,
                              wx.LEFT | wx.TOP | wx.BOTTOM, 10)

        # Language box
        language_box = wx.StaticBox(general_settings_screen, wx.ID_ANY,
                                    N_("Language"))
        language_box_sizer = wx.StaticBoxSizer(language_box, wx.VERTICAL)
        language_box_sizer.Add(cmb_language, 0,
                               wx.EXPAND | wx.ALL, 10)

        # Buttons box
        button_box = wx.BoxSizer(wx.HORIZONTAL)
        button_box.AddStretchSpacer(1)
        button_box.Add(btn_ok)
        button_box.Add(btn_cancel, 0, wx.LEFT, 10)
        button_box.Add(btn_apply, 0, wx.LEFT, 10)

        # Main sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(options_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.Add(language_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.AddStretchSpacer(1)
        main_sizer.Add(button_box, 0,
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
