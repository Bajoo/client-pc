# -*- coding: utf-8 -*-
import logging

import wx

from ...common.i18n import N_
from ...common import autorun, config
from ..common.language_box import LanguageBox
from ..base_view import BaseView
from ..translator import Translator


_logger = logging.getLogger(__name__)


class GeneralSettingsTab(wx.Panel, Translator):
    """
    General settings tab in the main window, which allows user to:
    * enable/disable start Bajoo on system startup
    * enable/disable contextual icon
    * enable/disable notifications
    * change application language
    """

    def __init__(self, parent, **kwarg):
        wx.Panel.__init__(self, parent, **kwarg)
        Translator.__init__(self)
        self._view = GeneralSettingsView(self)

        self._config = None

    def load_config(self, config):
        """
        Read config values in the config object and display on the UI.

        Args:
            config: the config object.
            If None, the current (self) config object will be used.
        """
        if config:
            self._config = config

        if self._config is None:
            _logger.debug("Null config object detected !!!")
            return

        # contextual_icon_shown = self._config.get('contextual_icon')
        # notifications_shown = self._config.get('notifications')
        # lang_code = self._config.get('lang')

        self.FindWindow('chk_launch_at_startup').Enable(
            autorun.can_autorun())
        self.FindWindow('chk_launch_at_startup').SetValue(
            autorun.is_autorun())

        # TODO: set to real value for next release
        self.FindWindow('chk_contextual_icon').SetValue(False)
        self.FindWindow('chk_notifications').SetValue(False)
        # TODO: change to language button & apply config

    def _on_applied(self, _event):
        launched_at_startup = \
            self.FindWindow('chk_launch_at_startup').GetValue()
        contextual_icon_shown = \
            self.FindWindow('chk_contextual_icon').GetValue()
        notifications_shown = \
            self.FindWindow('chk_notifications').GetValue()

        if self._config:
            self._config.set('contextual_icon', contextual_icon_shown)
            self._config.set('notifications', notifications_shown)

        # Set autorun and also change the config value
        autorun.set_autorun(launched_at_startup)
        self._config.set('autorun', launched_at_startup)

        _logger.info(
            'Bajoo autorun is %s',
            'enabled' if autorun.is_autorun() else 'disabled')

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self._view.notify_lang_change()


class GeneralSettingsView(BaseView):
    """View of the general settings screen"""

    def __init__(self, general_settings_screen):
        BaseView.__init__(self, general_settings_screen)

        # chk_launch_at_startup
        chk_launch_at_startup = wx.CheckBox(
            general_settings_screen, name='chk_launch_at_startup')

        # chk_contextual_icon
        chk_contextual_icon = wx.CheckBox(
            general_settings_screen, name='chk_contextual_icon')

        # chk_notifications
        chk_notifications = wx.CheckBox(
            general_settings_screen, name='chk_notifications')

        # TODO: disable for next release
        chk_contextual_icon.Disable()
        chk_notifications.Disable()

        # language_ctrl
        language_ctrl = LanguageBox(general_settings_screen,
                                    name='language_ctrl',
                                    current_lang_code=config.get('lang'))

        # Options box
        options_box = wx.StaticBox(general_settings_screen)
        options_box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        options_box_sizer_inside = self.make_sizer(wx.VERTICAL, [
            chk_launch_at_startup, chk_contextual_icon, chk_notifications])
        options_box_sizer.Add(options_box_sizer_inside)

        # Language box
        language_box = wx.StaticBox(general_settings_screen)
        language_box_sizer = wx.StaticBoxSizer(language_box, wx.VERTICAL)
        language_box_sizer.Add(language_ctrl, 0,
                               wx.EXPAND | wx.ALL, 10)
        self.add_i18n_child(language_ctrl)

        # Main sizer
        main_sizer = self.make_sizer(
            wx.VERTICAL, [options_box_sizer, language_box_sizer])

        general_settings_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            chk_launch_at_startup: N_("Launch Bajoo at system startup"),
            chk_contextual_icon: N_("Activate status icon "
                                    "and the contextual menu"),
            chk_notifications: N_("Display a notification when file download "
                                  "is finished"),
            language_box: N_("Language")
        })


def main():
    app = wx.App()
    win = wx.Frame(None, title='General Setttings')
    app.SetTopWindow(win)

    tab = GeneralSettingsTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
