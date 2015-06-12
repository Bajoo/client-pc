# -*- coding: utf-8 -*-

import wx

from ..ui_handler_of_connection import UIHandlerOfConnection
from .event_future import EventFuture
from .screen import HomeScreen


class HomeWindow(wx.Frame, UIHandlerOfConnection):
    """the welcome Window, displayed when the suer is not connected.

    This window is the main interface before the user connects. It contains
    all the screens about connexion and registration.

    the window inherits of UIHandlerOfConnection: It's the User interface used
    to ask the user his credentials and the other necessary information.

    The default screen is the HomeScreen, containing the connexion form.
    """

    def __init__(self):
        wx.Frame.__init__(self, parent=None, title='Bajoo')
        self._view = HomeWindowView(self)

    def wait_activation(self):
        pass

    def wait_user_resume(self):
        pass

    def ask_for_settings(self, folder_setting=True, key_setting=True):
        pass

    def get_register_or_connection_credentials(self, last_username=None,
                                               errors=None):
        self.Show(True)
        return EventFuture(self, wx.EVT_CLOSE).then(lambda evt: evt.Skip())

    def inform_user_is_connected(self):
        pass


class HomeWindowView(object):
    """View of the HomeWindow"""

    def __init__(self, window):
        self._current_screen = None

        s = wx.BoxSizer(wx.VERTICAL)

        self._current_screen = HomeScreen(window)

        s.Add(self._current_screen, proportion=1, flag=wx.EXPAND)
        s.SetSizeHints(window)  # Set default and min size of Window
        window.SetSizer(s)


def main():
    app = wx.App()
    win = HomeWindow()
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
