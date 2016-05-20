# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.newevent import NewCommandEvent

from ..base_view import BaseView
from ..event_promise import ensure_gui_thread
from ..translator import Translator
from ...__version__ import __version__
from ...common.i18n import N_
from ...common.strings import err2unicode


_logger = logging.getLogger(__name__)


class AdvancedSettingsTab(wx.Panel, Translator):
    """
    Advanced settings tab in the main window, which allows user to:
    * activate/deactivate debug mode
    * send crash reports
    * enable/disable application's auto update
    * enable/disable hidden file synchronization
    """

    GetUpdaterRequest, EVT_GET_UPDATER_REQUEST = NewCommandEvent()
    RestartRequest, EVT_RESTART_REQUEST = NewCommandEvent()

    def __init__(self, parent, **kwarg):
        wx.Panel.__init__(self, parent, **kwarg)
        Translator.__init__(self)

        self._updater = None
        self._view = AdvancedSettingsView(self)

        self._config = None

        event = self.GetUpdaterRequest(self.GetId())
        event.SetEventObject(self)
        wx.PostEvent(self, event)

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

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self._view.notify_lang_change()

    def set_updater(self, software_updater):
        self._updater = software_updater
        if self._updater.status == 'disabled':
            self._view.set_update_disabled()
        else:
            self._view.update_from_updater(self._updater)
            software_updater.status_changed.connect(
                self._update_status_changed)

    @ensure_gui_thread
    def _update_status_changed(self, status):
        self._view.update_from_updater(self._updater)

    def restart(self, _evt=None):
        _logger.debug('Send event to restart Bajoo')
        event = self.GetUpdaterRequest(self.GetId())
        event.SetEventObject(self)
        wx.PostEvent(self, event)

    def update_bajoo(self, _evt=None):
        _logger.debug('Manually check Bajoo update')
        self._updater.check_update()


class AdvancedSettingsView(BaseView):
    """View of the advanced settings screen"""

    def __init__(self, advanced_settings_screen):
        BaseView.__init__(self, advanced_settings_screen)

        self._last_status = None

        self._progress_bar = None
        self._update_btn = None
        self._restart_btn = None
        self._status_label = None
        self._new_version_label = None

        self._progress_bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        chk_send_report = wx.CheckBox(self.window, name='chk_send_report')
        chk_send_report.Disable()  # feature not implemented
        chk_debug_mode = wx.CheckBox(self.window, name='chk_debug_mode')

        # version_box
        lbl_current_version = wx.StaticText(self.window)

        self._status_label = wx.StaticText(self.window)

        self._update_status('loading')

        chk_auto_update = wx.CheckBox(self.window, name='chk_auto_update')
        chk_exclude_hidden_files = wx.CheckBox(self.window,
                                               name='chk_exclude_hidden_files')

        # report_debug_box
        __, report_debug_box_sizer = self._box_packing()
        self.make_sizer(wx.VERTICAL, [
            chk_send_report, chk_debug_mode
        ], sizer=report_debug_box_sizer)

        # updates_box
        updates_box, updates_box_sizer = self._box_packing()
        self.make_sizer(wx.VERTICAL, [
            lbl_current_version,
            self._status_label,
            self._progress_bar_sizer,
            self._btn_sizer,
            chk_auto_update
        ], sizer=updates_box_sizer)

        # exclude_box
        exclude_box, exclude_box_sizer = self._box_packing()
        self.make_sizer(wx.VERTICAL, [
            chk_exclude_hidden_files
        ], sizer=exclude_box_sizer)

        # main_sizer
        main_sizer = self.make_sizer(wx.VERTICAL, [
            report_debug_box_sizer,
            updates_box_sizer,
            exclude_box_sizer
        ])

        advanced_settings_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            lbl_current_version: (N_('Actual version: %s'), __version__),
            chk_send_report: N_('Send crash reports to Bajoo automatically'),
            chk_debug_mode: N_('Activate debug mode'),
            chk_auto_update: N_('Apply the updates automatically'),
            chk_exclude_hidden_files: N_("Don't synchronize hidden files"),
            updates_box: N_('Updates')
        })

    def update_from_updater(self, updater):
        self._update_status(updater.status, updater)

        if updater.status in ('downloading', 'ready', 'installing'):
            if not self._progress_bar:
                self._progress_bar = wx.Gauge(self.window,
                                              range=updater.dl_total_size or 0)
                self._progress_bar_sizer.Add(self._progress_bar, proportion=1)

            if updater.status == 'downloading':
                if updater.dl_total_size:
                    self._progress_bar.SetValue(updater.dl_received)
                else:
                    self._progress_bar.Pulse()
            else:
                self._progress_bar.SetValue(99)  # almost done.
        elif self._progress_bar is not None:
            self._progress_bar = None
            self._progress_bar_sizer.Clear(True)

        if updater.status in ('idle', 'aborted', 'error'):
            if self._update_btn is None:
                self._update_btn = wx.Button(self.window)
                self._update_btn.Bind(wx.EVT_BUTTON, self.window.update_bajoo)
                self._btn_sizer.AddStretchSpacer()
                self._btn_sizer.Add(self._update_btn)
                self.register_many_i18n('SetLabelText', {
                    self._update_btn: N_('Check updates')
                })
        elif self._update_btn is not None:
            self._btn_sizer.Detach(self._update_btn)
            self._update_btn.Destroy()
            self._update_btn = None

        if updater.status == 'done':
            if self._restart_btn is None:
                self._restart_btn = wx.Button(self.window)
                self._restart_btn.Bind(wx.EVT_BUTTON, self.window.restart)
                self._btn_sizer.AddStretchSpacer()
                self._btn_sizer.Add(self._restart_btn)
                self.register_many_i18n('SetLabelText', {
                    self._restart_btn: N_('Restart')
                })
        elif self._restart_btn is not None:
            self._btn_sizer.Detach(self._restart_btn)
            self._restart_btn.Destroy()
            self._restart_btn = None

        self.window.GetSizer().Layout()

    def set_update_disabled(self):
        self.window.FindWindow('chk_auto_update').Disable()
        self._update_status('disabled')

    def _box_packing(self):
        box = wx.StaticBox(self.window)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        return box, sizer

    def _update_status(self, status='loading', updater=None):
        if self._last_status == status and status != 'error':
            return
        self._last_status = status

        err = None
        new_version = None
        if updater:
            err = updater.exception
            new_version = updater.new_version

        status2txt = {
            'loading': N_('Checking last update available ...'),
            'disabled': N_('Automatic Bajoo updates are available only for the'
                           ' packaged Windows version.'),
            'aborted': N_('Update attempt has been aborted.'),
            'idle': N_('Your software is up to date.'),
            'searching': N_('Searching new updates ...'),
            'found': (N_('New version found: %s'), new_version),
            'downloading': N_('Downloading the new version ...'),
            'retrying': N_('Retrying after an error happened ...'),
            'error': (N_('An error happened:\n%s'), err2unicode(err)),
            'ready': N_('New version ready to be installed ...'),
            'installing': N_('Install in progress ...'),
            'cleaning up': N_('Cleaning up old files'),
            'done': (N_('Bajoo has been updated to version %s. It must be '
                        'restarted to apply changes.'), new_version)
        }
        self.remove_i18n_child(self._status_label)
        self.register_many_i18n('SetLabelText', {
            self._status_label: status2txt.get(status, status)
        })


def main():
    from ...common.signal import Signal
    app = wx.App()
    win = wx.Frame(None, title=N_('Advanced settings'))
    app.SetTopWindow(win)

    class MockUpdater(object):
        status_changed = Signal()
        status = 'downloading'
        dl_received = 3366666
        dl_total_size = 13456789
        exception = None
        new_version = None

    def send_updater(event):
        event.EventObject.set_updater(MockUpdater())

    app.Bind(AdvancedSettingsTab.EVT_GET_UPDATER_REQUEST, send_updater)

    tab = AdvancedSettingsTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
