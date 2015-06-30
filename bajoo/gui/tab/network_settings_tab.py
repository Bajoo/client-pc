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

        # chk_limit_incoming_debit
        chk_limit_incoming_debit = wx.CheckBox(
            network_settings_screen, wx.ID_ANY,
            N_("Limit incoming debit (download)"),
            name='chk_limit_incoming_debit')

        # txt_incoming_limit_value
        txt_incoming_limit_value = wx.TextCtrl(
            network_settings_screen, wx.ID_ANY,
            name='txt_incoming_limit_value')

        # chk_limit_outgoing_debit
        chk_limit_outgoing_debit = wx.CheckBox(
            network_settings_screen, wx.ID_ANY,
            N_("Limit outgoing debit (upload)"),
            name='chk_limit_outgoing_debit')

        # txt_outgoing_limit_value
        txt_outgoing_limit_value = wx.TextCtrl(
            network_settings_screen, wx.ID_ANY,
            name='txt_outgoing_limit_value')

        # bandwidth_grid_sizer: Align TextCtrls with other static texts
        flag, border = wx.TOP, 3
        bandwidth_grid_sizer = wx.GridBagSizer(10, 5)
        bandwidth_grid_sizer.Add(chk_limit_incoming_debit, (0, 0),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(txt_incoming_limit_value, (0, 1))
        bandwidth_grid_sizer.Add(wx.StaticText(network_settings_screen,
                                               wx.ID_ANY, N_("Kb/s")), (0, 2),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(chk_limit_outgoing_debit, (1, 0),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(txt_outgoing_limit_value, (1, 1))
        bandwidth_grid_sizer.Add(wx.StaticText(network_settings_screen,
                                               wx.ID_ANY, N_("Kb/s")), (1, 2),
                                 flag=flag, border=border)

        # Bandwidth box
        bandwidth_box = wx.StaticBox(
            network_settings_screen, wx.ID_ANY,
            N_("Bandwidth"))
        bandwidth_box_sizer = wx.StaticBoxSizer(bandwidth_box)
        bandwidth_box_sizer.Add(bandwidth_grid_sizer, 1, wx.ALL, 5)

        # Proxy box
        proxy_box = wx.StaticBox(
            network_settings_screen, wx.ID_ANY,
            N_("Proxy"))
        proxy_box_sizer = wx.StaticBoxSizer(proxy_box)

        # Buttons box
        buttons_box = self.create_settings_button_box(
            network_settings_screen)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(bandwidth_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.Add(proxy_box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.AddStretchSpacer(1)
        main_sizer.Add(buttons_box, 0,
                       wx.EXPAND | wx.ALL, 10)

        network_settings_screen.SetSizer(main_sizer)


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('My Account'))
    app.SetTopWindow(win)

    tab = NetworkSettingsTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
