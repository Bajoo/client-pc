# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView
from ...__version__ import __version__


_logger = logging.getLogger(__name__)


class AdvancedSettingsTab(wx.Panel):
    """
    Advanced settings tab in the main window, which allows user to:
    * activate/deactivate debug mode
    * send crash reports
    * enable/disable application's auto update
    * enable/disable hidden file synchronization
    """

    CheckUpdatesRequest, EVT_CHECK_UPDATES_REQUEST = NewCommandEvent()

    def __init__(self, parent, **kwarg):
        wx.Panel.__init__(self, parent, **kwarg)
        self._view = AdvancedSettingsView(self)

        self._config = None

    def load_config(self, config):
        if config:
            self._config = config

        if self._config is None:
            _logger.debug("Null config object detected !!!")
            return

        self.FindWindow('chk_auto_update').SetValue(
            self._config.get('auto_update'))
        self.FindWindow('chk_debug_mode').SetValue(
            self._config.get('debug_mode'))
        self.FindWindow('chk_exclude_hidden_files').SetValue(
            self._config.get('exclude_hidden_files'))

        self.Bind(wx.EVT_BUTTON, self._on_check_update,
                  self.FindWindow('btn_check_updates'))

    def _on_applied(self, _event):
        self._config.set(
            'auto_update',
            self.FindWindow('chk_auto_update').GetValue())
        self._config.set(
            'debug_mode',
            self.FindWindow('chk_debug_mode').GetValue())
        self._config.set(
            'exclude_hidden_files',
            self.FindWindow('chk_exclude_hidden_files').GetValue())

    def _on_check_update(self, _event):
        event = AdvancedSettingsTab.CheckUpdatesRequest(self.GetId())
        wx.PostEvent(self, event)


class AdvancedSettingsView(BaseView):
    """View of the advanced settings screen"""

    def __init__(self, advanced_settings_screen):
        BaseView.__init__(self, advanced_settings_screen)

        # chk_send_report
        chk_send_report = wx.CheckBox(
            advanced_settings_screen, name='chk_send_report')
        chk_send_report.Disable()

        # chk_debug_mode
        chk_debug_mode = wx.CheckBox(
            advanced_settings_screen, name='chk_debug_mode')

        # version_box
        lbl_version_desc = wx.StaticText(advanced_settings_screen)
        lbl_version = wx.StaticText(
            advanced_settings_screen, label=__version__, name='lbl_version')
        version_box = self.make_sizer(wx.HORIZONTAL, [
            lbl_version_desc, lbl_version], outside_border=False)

        # chk_auto_update
        chk_auto_update = wx.CheckBox(
            advanced_settings_screen, name='chk_auto_update')

        # btn_check_updates
        btn_check_updates = wx.Button(
            advanced_settings_screen, name='btn_check_updates')

        # chk_exclude_hidden_files
        chk_exclude_hidden_files = wx.CheckBox(
            advanced_settings_screen, name='chk_exclude_hidden_files')

        # report_debug_box
        report_debug_box = wx.StaticBox(advanced_settings_screen, wx.ID_ANY)
        report_debug_box_sizer = wx.StaticBoxSizer(
            report_debug_box, wx.VERTICAL)
        report_debug_box_sizer_inside = self.make_sizer(
            wx.VERTICAL, [chk_send_report, chk_debug_mode])
        report_debug_box_sizer.Add(report_debug_box_sizer_inside)

        # updates_box
        updates_box = wx.StaticBox(advanced_settings_screen)
        updates_box_sizer = wx.StaticBoxSizer(updates_box, wx.HORIZONTAL)
        updates_box_sizer_inside = self.make_sizer(
            wx.VERTICAL, [version_box, chk_auto_update])
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
        main_sizer = self.make_sizer(
            wx.VERTICAL, [report_debug_box_sizer, updates_box_sizer,
                          exclude_box_sizer])

        advanced_settings_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            lbl_version_desc: N_('Actual version:'),
            chk_send_report: N_('Send crash reports to Bajoo automatically'),
            chk_debug_mode: N_('Activate debug mode'),
            chk_auto_update: N_('Apply the updates automatically'),
            btn_check_updates: N_('Check for updates'),
            chk_exclude_hidden_files: N_("Don't synchronize hidden files"),
            updates_box: N_('Updates')
        })


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
