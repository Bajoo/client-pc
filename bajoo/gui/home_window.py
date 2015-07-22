# -*- coding: utf-8 -*-

import wx

from ..common.future import wait_one
from ..ui_handler_of_connection import UIHandlerOfConnection
from .base_view import BaseView
from .event_future import EventFuture, ensure_gui_thread
from .screen import ActivationScreen, HomeScreen, SetupConfigScreen


class HomeWindow(wx.Frame, UIHandlerOfConnection):
    """the welcome Window, displayed when the suer is not connected.

    This window is the main interface before the user connects. It contains
    all the screens about connexion and registration.

    the window inherits of UIHandlerOfConnection: It's the User interface used
    to ask the user his credentials and the other necessary information.

    The default screen is the HomeScreen, containing the connexion form.
    """

    @ensure_gui_thread
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title='Bajoo')
        self._view = HomeWindowView(self)

        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, event):
        """Hide the window instead of closing."""
        if event.CanVeto():
            event.Veto()
            self.Hide()

    @ensure_gui_thread
    def wait_activation(self):
        self._view.set_screen(ActivationScreen)
        self._view.current_screen.reset_form()

        self.Bind(ActivationScreen.EVT_ACTIVATION_DELAYED,
                  lambda _evt: self.Close())

        def callback(evt):
            self.Unbind(ActivationScreen.EVT_ACTIVATION_DELAYED)
            return None

        f = EventFuture(self, ActivationScreen.EVT_ACTIVATION_DONE)
        return f.then(callback)

    @ensure_gui_thread
    def ask_for_settings(self, folder_setting=True, key_setting=True,
                         root_folder_error=None, gpg_error=None):
        self._view.set_screen(SetupConfigScreen)
        self._view.current_screen.reset_form(
            folder_setting, key_setting,
            root_folder_error=root_folder_error, gpg_error=gpg_error)

        f = EventFuture(self, SetupConfigScreen.EVT_SUBMIT)
        return f.then(lambda data: (data.bajoo_folder, data.passphrase))

    @ensure_gui_thread
    def get_register_or_connection_credentials(self, last_username=None,
                                               errors=None):

        self._view.set_screen(HomeScreen)
        self._view.current_screen.reset_form(last_username, errors)
        self.Show(True)

        def callback(evt):
            if evt.GetEventType() == HomeScreen.EVT_CONNECTION_SUBMIT.typeId:
                action = 'connection'
            else:
                action = 'register'
            return action, evt.username, evt.password

        return wait_one([
            EventFuture(self, HomeScreen.EVT_CONNECTION_SUBMIT),
            EventFuture(self, HomeScreen.EVT_REGISTER_SUBMIT),
        ], cancel_others=True).then(callback)

    @ensure_gui_thread
    def inform_user_is_connected(self):
        pass

    def notify_lang_change(self):
        self._view.notify_lang_change()


class HomeWindowView(BaseView):
    """View of the HomeWindow

    Attributes:
        current_screen (wx.Window): the screen actually active.
    """

    def __init__(self, window):
        BaseView.__init__(self, window)

        self.current_screen = None
        s = wx.BoxSizer(wx.VERTICAL)
        window.SetSizer(s)

        # List of all already instantiated screens.
        # The key is the Screen class.
        # The value is the SizerItem, corresponding to the screen.
        self._screen_map = {}

    def set_screen(self, screen_class):
        """Change the current screen.

        If a screen of the same class is already instantiated, it's reused.
        Only one screen is displayed at the same time.
        """
        sizer = self.window.GetSizer()

        sizer_item = self._screen_map.get(screen_class)
        if sizer_item:
            self.current_screen = sizer_item.GetWindow()
        if not sizer_item:
            self.current_screen = screen_class(self.window)
            sizer_item = sizer.Add(self.current_screen, proportion=1,
                                   flag=wx.EXPAND)
            self._screen_map[screen_class] = sizer_item
            self.add_i18n_child(self.current_screen)

        sizer.ShowItems(False)
        sizer_item.Show(True)
        sizer.SetSizeHints(self.window)  # Set default and min size of Window


def main():
    app = wx.App()
    win = HomeWindow()
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
