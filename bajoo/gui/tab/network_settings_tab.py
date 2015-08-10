# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.masked import NumCtrl

from ...common.i18n import N_
from ..base_view import BaseView
from ..form import ProxyForm


_logger = logging.getLogger(__name__)


class NetworkSettingsTab(wx.Panel):
    """
    Network settings tab in the main window, which allows user to:
    * change download/upload bandwidth
    * change proxy settings
    """

    def __init__(self, parent, **kwarg):
        wx.Panel.__init__(self, parent, **kwarg)
        self._view = NetworkSettingsView(self)

        self._config = None

        self.Bind(wx.EVT_CHECKBOX, self._on_limit_download_check_changed,
                  self.FindWindow('chk_limit_incoming_debit'))
        self.Bind(wx.EVT_CHECKBOX, self._on_limit_upload_check_changed,
                  self.FindWindow('chk_limit_outgoing_debit'))

    def load_config(self, config):
        if config:
            self._config = config

        if self._config is None:
            _logger.debug("Null config object detected !!!")
            return

        # The proxy form config has already been loaded
        # So load only other fields.
        download_max_speed = self._config.get('download_max_speed')
        limit_download = download_max_speed is not None

        upload_max_speed = self._config.get('upload_max_speed')
        limit_upload = upload_max_speed is not None

        self.FindWindow('chk_limit_incoming_debit') \
            .SetValue(limit_download)
        # Default value: 100 KB/s
        self.FindWindow('txt_incoming_limit_value') \
            .SetValue(download_max_speed if limit_download else 100)
        self.FindWindow('txt_incoming_limit_value') \
            .Enable(limit_download)
        self.FindWindow('chk_limit_outgoing_debit') \
            .SetValue(limit_upload)
        # Default value: 100 KB/s
        self.FindWindow('txt_outgoing_limit_value') \
            .SetValue(upload_max_speed if limit_upload else 100)
        self.FindWindow('txt_outgoing_limit_value') \
            .Enable(limit_upload)

        self.FindWindow('proxy_form').populate()

    def _on_limit_download_check_changed(self, event):
        limit_download = self.FindWindow('chk_limit_incoming_debit') \
            .GetValue()
        self.FindWindow('txt_incoming_limit_value') \
            .Enable(limit_download)

    def _on_limit_upload_check_changed(self, event):
        limit_upload = self.FindWindow('chk_limit_outgoing_debit') \
            .GetValue()
        self.FindWindow('txt_outgoing_limit_value') \
            .Enable(limit_upload)

    def _on_applied(self, _event):
        download_max_speed = upload_max_speed = None

        txt_incoming_limit = self.FindWindow('txt_incoming_limit_value')
        if self.FindWindow('chk_limit_incoming_debit').IsChecked():
            download_max_speed = float(txt_incoming_limit.GetValue())

        txt_outgoing_limit = self.FindWindow('txt_outgoing_limit_value')
        if self.FindWindow('chk_limit_outgoing_debit').IsChecked():
            upload_max_speed = float(txt_outgoing_limit.GetValue())

        if self._config:
            self._config.set('download_max_speed', download_max_speed)
            self._config.set('upload_max_speed', upload_max_speed)

        proxy_data = self.FindWindow('proxy_form').get_data()
        self._config.set('proxy_mode', proxy_data.get('proxy_mode'))
        self._config.set('proxy_type', proxy_data.get('proxy_type'))
        self._config.set('proxy_url', proxy_data.get('server_uri'))
        self._config.set('proxy_port', proxy_data.get('server_port'))
        self._config.set('proxy_user', proxy_data.get('username'))
        self._config.set('proxy_password', proxy_data.get('password'))


class NetworkSettingsView(BaseView):
    """View of the network settings screen"""

    def __init__(self, network_settings_screen):
        BaseView.__init__(self, network_settings_screen)

        # chk_limit_incoming_debit
        chk_limit_incoming_debit = wx.CheckBox(
            network_settings_screen, name='chk_limit_incoming_debit')

        # txt_incoming_limit_value
        txt_incoming_limit_value = NumCtrl(
            network_settings_screen,
            name='txt_incoming_limit_value', min=1)
        lbl_incoming_unit = wx.StaticText(network_settings_screen)

        # chk_limit_outgoing_debit
        chk_limit_outgoing_debit = wx.CheckBox(
            network_settings_screen, name='chk_limit_outgoing_debit')

        # txt_outgoing_limit_value
        txt_outgoing_limit_value = NumCtrl(
            network_settings_screen,
            name='txt_outgoing_limit_value', min=1)
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

        main_sizer = self.make_sizer(
            wx.VERTICAL,
            [bandwidth_box_sizer, proxy_form])

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
