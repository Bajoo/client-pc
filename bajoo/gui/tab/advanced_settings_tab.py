# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView
from ...__version__ import __version__


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

        # chk_send_report
        chk_send_report = wx.CheckBox(
            advanced_settings_screen, wx.ID_ANY,
            N_('Send crash reports to Bajoo automatically'),
            name='chk_send_report')

        # chk_debug_mode
        chk_debug_mode = wx.CheckBox(
            advanced_settings_screen, wx.ID_ANY,
            N_('Activate debug mode'),
            name='chk_debug_mode')

        # lbl_version
        lbl_version = wx.StaticText(
            advanced_settings_screen, wx.ID_ANY,
            N_('Actual verion') + ": " + __version__,
            name='lbl_version')

        # chk_auto_update
        chk_auto_update = wx.CheckBox(
            advanced_settings_screen, wx.ID_ANY,
            N_('Apply the updates automatically'),
            name='chk_auto_update')

        # btn_check_updates
        btn_check_updates = wx.Button(
            advanced_settings_screen, wx.ID_ANY,
            N_('Check for updates'),
            name='btn_verify_updates')

        # chk_exclude_hidden_files
        chk_exclude_hidden_files = wx.CheckBox(
            advanced_settings_screen, wx.ID_ANY,
            N_("Don't synchronize hidden files"),
            name='chk_exclude_hidden_files')

        # buttons_box
        buttons_box = self.create_settings_button_box(
            advanced_settings_screen)

        # report_debug_box
        report_debug_box = wx.StaticBox(advanced_settings_screen, wx.ID_ANY)
        report_debug_box_sizer = wx.StaticBoxSizer(
            report_debug_box, wx.VERTICAL)
        report_debug_box_sizer_inside = self.make_sizer(
            wx.VERTICAL, [chk_send_report, chk_debug_mode])
        report_debug_box_sizer.Add(report_debug_box_sizer_inside)

        # updates_box
        updates_box = wx.StaticBox(advanced_settings_screen, wx.ID_ANY,
                                   N_('Updates'))
        updates_box_sizer = wx.StaticBoxSizer(updates_box, wx.HORIZONTAL)
        updates_box_sizer_inside = self.make_sizer(
            wx.VERTICAL, [lbl_version, chk_auto_update])
        updates_box_sizer.Add(updates_box_sizer_inside)
        updates_box_sizer.AddStretchSpacer(1)

        updates_box_sizer.Add(btn_check_updates, 0, wx.TOP | wx.RIGHT, 10)
        # exclude_box
        exclude_box = wx.StaticBox(advanced_settings_screen, wx.ID_ANY)
        exclude_box_sizer = wx.StaticBoxSizer(exclude_box, wx.VERTICAL)
        exclude_box_sizer_inside = self.make_sizer(
            wx.VERTICAL, [chk_exclude_hidden_files])
        exclude_box_sizer.Add(exclude_box_sizer_inside)

        # main_sizer
        proportion = 0
        flag = wx.EXPAND | wx.ALL
        border = 10
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(report_debug_box_sizer, proportion, flag, border)
        main_sizer.Add(updates_box_sizer, proportion, flag, border)
        main_sizer.Add(exclude_box_sizer, proportion, flag, border)
        main_sizer.AddStretchSpacer()
        main_sizer.Add(buttons_box, proportion, flag, border)

        advanced_settings_screen.SetSizer(main_sizer)


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('Advanced Settings'))
    app.SetTopWindow(win)

    tab = AdvancedSettingsTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
