# -*- coding: utf-8 -*-

import wx

from ..ui_handler_of_connection import UIHandlerOfConnection


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
        pass

    def inform_user_is_connected(self):
        pass


class HomeWindowView(wx.Panel):
    """View of the HomeWindow"""

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        s = wx.BoxSizer(wx.VERTICAL)

        # TODO: insert elements.

        self.SetSizer(s)
        s.SetSizeHints(self.GetParent())  # Set default and min size of Window


def main():
    app = wx.App()
    win = HomeWindow()
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
