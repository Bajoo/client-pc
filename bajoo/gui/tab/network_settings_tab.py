# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView
from ..form import ProxyForm


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
            network_settings_screen, name='chk_limit_incoming_debit')

        # txt_incoming_limit_value
        txt_incoming_limit_value = wx.TextCtrl(
            network_settings_screen, name='txt_incoming_limit_value')
        lbl_incoming_unit = wx.StaticText(network_settings_screen)

        # chk_limit_outgoing_debit
        chk_limit_outgoing_debit = wx.CheckBox(
            network_settings_screen, name='chk_limit_outgoing_debit')

        # txt_outgoing_limit_value
        txt_outgoing_limit_value = wx.TextCtrl(
            network_settings_screen, name='txt_outgoing_limit_value')
        lbl_outgoing_unit = wx.StaticText(network_settings_screen)

        # bandwidth_grid_sizer: Align TextCtrls with other static texts
        flag, border = wx.TOP, 3
        bandwidth_grid_sizer = wx.GridBagSizer(10, 5)
        bandwidth_grid_sizer.Add(chk_limit_incoming_debit, (0, 0),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(txt_incoming_limit_value, (0, 1))
        bandwidth_grid_sizer.Add(lbl_incoming_unit, (0, 2),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(chk_limit_outgoing_debit, (1, 0),
                                 flag=flag, border=border)
        bandwidth_grid_sizer.Add(txt_outgoing_limit_value, (1, 1))
        bandwidth_grid_sizer.Add(lbl_outgoing_unit, (1, 2),
                                 flag=flag, border=border)

        # Bandwidth box
        bandwidth_box = wx.StaticBox(network_settings_screen)
        bandwidth_box_sizer = wx.StaticBoxSizer(bandwidth_box)
        bandwidth_box_sizer.Add(bandwidth_grid_sizer, 1, wx.ALL, 5)

        # proxy form
        proxy_form = ProxyForm(network_settings_screen, name='proxy_form')

        # Buttons box
        buttons_box = self.create_settings_button_box(
            network_settings_screen)

        main_sizer = self.make_sizer(
            wx.VERTICAL,
            [bandwidth_box_sizer, proxy_form, None, buttons_box])

        network_settings_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            chk_limit_incoming_debit: N_("Limit incoming debit (download)"),
            chk_limit_outgoing_debit: N_("Limit outgoing debit (upload)"),
            lbl_incoming_unit: N_("Kb/s"),
            lbl_outgoing_unit: N_("Kb/s"),
            bandwidth_box: N_("Bandwidth")
        })


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
