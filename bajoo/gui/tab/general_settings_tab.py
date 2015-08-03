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
    * enable/disable contextual icon
    * enable/disable notifications
    * change application language
    """

    ConfigRequest, EVT_CONFIG_REQUEST = NewCommandEvent()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = GeneralSettingsView(self)

        self._config = None

        self.Bind(wx.EVT_BUTTON, self._on_finished, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._on_cancelled, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._on_applied, id=wx.ID_APPLY)

    def Show(self, show=True):
        wx.PostEvent(self, self.ConfigRequest(self.GetId()))

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

        launched_at_startup = self._config.get('launched_at_startup')
        contextual_icon_shown = self._config.get('contextual_icon')
        notifications_shown = self._config.get('notifications')
        lang_code = self._config.get('lang')

        self.FindWindow('chk_launch_at_startup').SetValue(launched_at_startup)
        self.FindWindow('chk_contextual_icon').SetValue(contextual_icon_shown)
        self.FindWindow('chk_notifications').SetValue(notifications_shown)
        # TODO: change to language button & apply config

    def _on_finished(self, _event):
        """
        Apply the setting changes & send event to close the window.
        """
        self._on_applied(_event)
        # TODO: send event to close the window

    def _on_cancelled(self, _event):
        """
        Handle the click event on the button Cancel:
        Reset the UI elements according to the current config.
        """
        self.load_config(None)

    def _on_applied(self, _event):
        launched_at_startup = \
            self.FindWindow('chk_launch_at_startup').GetValue()
        contextual_icon_shown = \
            self.FindWindow('chk_contextual_icon').GetValue()
        notifications_shown = \
            self.FindWindow('chk_notifications').GetValue()

        if self._config:
            self._config.set('launched_at_startup', launched_at_startup)
            self._config.set('contextual_icon', contextual_icon_shown)
            self._config.set('notifications', notifications_shown)


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

        # cmb_language
        cmb_language = wx.ComboBox(
            general_settings_screen, style=wx.CB_READONLY, name='cmb_language')

        # Options box
        options_box = wx.StaticBox(general_settings_screen)
        options_box_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        options_box_sizer_inside = self.make_sizer(
            wx.VERTICAL,
            [chk_launch_at_startup, chk_contextual_icon, chk_notifications])
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
            chk_contextual_icon: N_("Activate status icon "
                                    "and the contextual menu"),
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
