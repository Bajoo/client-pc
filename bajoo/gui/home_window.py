# -*- coding: utf-8 -*-

import wx

from ..common.future import wait_one
from ..ui_handler_of_connection import UIHandlerOfConnection, UserInterrupt
from .event_future import EventFuture, ensure_gui_thread
from .screen import HomeScreen


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

    @ensure_gui_thread
    def wait_activation(self):
        pass

    @ensure_gui_thread
    def wait_user_resume(self):
        pass

    @ensure_gui_thread
    def ask_for_settings(self, folder_setting=True, key_setting=True):
        pass

    @ensure_gui_thread
    def get_register_or_connection_credentials(self, last_username=None,
                                               errors=None):

        self._view.current_screen.reset_form(last_username, errors)
        self.Show(True)

        def callback(evt):
            if evt.GetEventType() == wx.EVT_CLOSE.typeId:
                raise UserInterrupt()
            if evt.GetEventType() == HomeScreen.EVT_CONNECTION_SUBMIT.typeId:
                action = 'connection'
            else:
                action = 'register'
            return action, evt.username, evt.password

        return wait_one([
            EventFuture(self, HomeScreen.EVT_CONNECTION_SUBMIT),
            EventFuture(self, HomeScreen.EVT_REGISTER_SUBMIT),
            EventFuture(self, wx.EVT_CLOSE)
        ], cancel_others=True).then(callback)

    @ensure_gui_thread
    def inform_user_is_connected(self):
        pass


class HomeWindowView(object):
    """View of the HomeWindow

    Attributes:
        current_screen (wx.Window): the screen actually active.
    """

    def __init__(self, window):
        self.current_screen = None

        s = wx.BoxSizer(wx.VERTICAL)

        self.current_screen = HomeScreen(window)

        s.Add(self.current_screen, proportion=1, flag=wx.EXPAND)
        s.SetSizeHints(window)  # Set default and min size of Window
        window.SetSizer(s)


def main():
    app = wx.App()
    win = HomeWindow()
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
