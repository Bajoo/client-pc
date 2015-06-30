# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class NetworkSettingsTab(wx.Panel):
    """
    Network settings tab in the main window, which allows user to:
    * change download/upload bandwidth
    * change proxy settings
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = NetworkSettingsView(self)


class NetworkSettingsView(BaseView):
    """View of the network settings screen"""

    def __init__(self, network_settings_screen):
        BaseView.__init__(self, network_settings_screen)

        bandwidth_box = wx.StaticBox(
            network_settings_screen, wx.ID_ANY,
            N_("Bandwidth"))
        bandwidth_box_sizer = wx.StaticBoxSizer(bandwidth_box)

        buttons_box = self.create_settings_button_box(
            network_settings_screen)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(bandwidth_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.AddStretchSpacer(1)
        main_sizer.Add(buttons_box, 0,
                       wx.EXPAND | wx.ALL, 10)

        network_settings_screen.SetSizer(main_sizer)
        main_sizer.SetSizeHints(network_settings_screen.GetTopLevelParent())


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('My Account'))
    app.SetTopWindow(win)
    NetworkSettingsTab(win)
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
