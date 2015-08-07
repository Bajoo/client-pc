# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent
from wx.lib.agw.hyperlink import HyperLinkCtrl

from ...common.i18n import N_
from ...common.util import human_readable_bytes
from ..base_view import BaseView
from ...common import config
from ...common.util import open_folder


class AccountTab(wx.Panel):
    """
    Account settings tab in the main window, which allows user to:
    * view account information like email, quota
    * change password
    * change offer plan
    * reset encryption passphrase
    * disconnect
    """

    DataRequestEvent, EVT_DATA_REQUEST = NewCommandEvent()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = AccountView(self)
        self._data = {
            'email': '',
            'account_type': '',
            'n_shares': 0,
            'quota': 1,
            'quota_used': 0
        }

        # TODO: disable for next release
        self.FindWindow('btn_disconnect').Disable()
        self.FindWindow('btn_reinit_passphrase').Disable()
        self.FindWindow('btn_change_password').Disable()

        self.Bind(wx.EVT_BUTTON, self._on_open_bajoo_folder,
                  self.FindWindowByName('btn_open_bajoo_folder'))

    def set_data(self, key, value):
        self._data[key] = value

    def populate(self):
        quota_str = human_readable_bytes(self._data['quota'])
        quota_used_str = human_readable_bytes(self._data['quota_used'])
        quota_percentage = 0

        # TODO: human readable size
        if 'quota' in self._data.keys() \
                and 'quota_used' in self._data.keys():
            quota_percentage = \
                self._data['quota_used'] * 100 / float(self._data['quota'])

        self.FindWindow('lbl_email') \
            .SetLabelText(self._data['email'])
        self.FindWindow('lbl_account_type') \
            .SetLabelText(self._data['account_type'])

        # re-register quota info text
        self._view.remove_i18n(self.FindWindow('lbl_quota_info').SetLabelText)
        self._view.register_i18n(
            self.FindWindow('lbl_quota_info').SetLabelText,
            N_("%d share folder use %s, so %0.2f%% of your Bajoo storage."),
            (self._data['n_shares'], quota_used_str, quota_percentage))

        self.FindWindow('gauge_quota').SetValue(quota_percentage)
        self.FindWindow('gauge_text_min').SetLabelText('0')
        self.FindWindow('gauge_text_value').SetLabelText(quota_used_str)
        self.FindWindow('gauge_text_max').SetLabelText(quota_str)

    def _on_open_bajoo_folder(self, event):
        path = config.get('root_folder')
        open_folder(path)

    def Show(self, show=True):
        event = AccountTab.DataRequestEvent(self.GetId())
        wx.PostEvent(self, event)


class AccountView(BaseView):
    """View of the account screen"""

    def __init__(self, account_screen):
        BaseView.__init__(self, account_screen)

        account_info_box = wx.StaticBox(account_screen, -1)
        box_sizer = wx.StaticBoxSizer(account_info_box, wx.VERTICAL)

        # email_box
        lbl_email_description = wx.StaticText(
            account_screen, name='lbl_email_description')
        lbl_email = wx.StaticText(
            account_screen, name='lbl_email')
        email_box = self.make_sizer(
            wx.HORIZONTAL, [lbl_email_description, lbl_email],
            outside_border=False)

        # account_type_box
        lbl_account_type_desc = wx.StaticText(
            account_screen, name='lbl_account_type_desc')
        lbl_account_type = wx.StaticText(
            account_screen, name='lbl_account_type')
        account_type_box = self.make_sizer(
            wx.HORIZONTAL, [lbl_account_type_desc, lbl_account_type],
            outside_border=False)

        # btn_change_offer
        # TODO: URL
        btn_change_offer = HyperLinkCtrl(
            account_screen, URL="https://www.bajoo.fr",
            name='btn_change_offer')

        # lbl_quota_info
        lbl_quota_info = wx.StaticText(
            account_screen, wx.ID_ANY,
            "quota_info", name='lbl_quota_info')

        # btn_disconnect
        btn_disconnect = wx.Button(
            account_screen, name='btn_disconnect')

        # btn_open_bajoo_folder
        btn_open_bajoo_folder = wx.Button(
            account_screen, name='btn_open_bajoo_folder')

        # btn_reinit_passphrase
        btn_reinit_passphrase = wx.Button(
            account_screen, name='btn_reinit_passphrase')
        btn_reinit_passphrase.SetMinSize(
            (200, btn_reinit_passphrase.GetSize()[1]))

        # btn_change_password
        btn_change_password = wx.Button(
            account_screen, name='btn_change_password')
        btn_change_password.SetMinSize(
            (200, btn_change_password.GetSize()[1]))

        # gauge_quota
        gauge_quota = wx.Gauge(
            account_screen, wx.ID_ANY, 100,
            name='gauge_quota')

        # TODO: set proper quota text
        gauge_text_min = wx.StaticText(
            account_screen, wx.ID_ANY,
            "min", name='gauge_text_min')
        gauge_text_value = wx.StaticText(
            account_screen, wx.ID_ANY,
            "value", name='gauge_text_value')
        gauge_text_max = wx.StaticText(
            account_screen, wx.ID_ANY,
            "max", name='gauge_text_max')

        info_text_sizer = wx.BoxSizer(wx.VERTICAL)
        info_text_sizer.Add(email_box)
        info_text_sizer.Add(account_type_box, 0, wx.TOP, 10)
        info_text_sizer.Add(btn_change_offer, 0, wx.TOP, 10)
        info_text_sizer.Add(lbl_quota_info, 0, wx.TOP, 10)

        info_button_sizer = wx.BoxSizer(wx.VERTICAL)
        info_button_sizer.Add(btn_disconnect, 0, wx.EXPAND | wx.RIGHT, 0)
        info_button_sizer.Add(btn_open_bajoo_folder, 0,
                              wx.EXPAND | wx.TOP, 10)

        info_text_button_sizer = self.make_sizer(
            wx.HORIZONTAL, [info_text_sizer, None, info_button_sizer], False)

        gauge_text_sizer = self.make_sizer(
            wx.HORIZONTAL, [gauge_text_min, None, gauge_text_value,
                            None, gauge_text_max], False, 0, 0)

        box_sizer.Add(info_text_button_sizer, 1, wx.EXPAND | wx.ALL, 10)
        box_sizer.Add(gauge_quota, 0,
                      wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        box_sizer.Add(gauge_text_sizer, 0,
                      wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        main_sizer = self.make_sizer(
            wx.VERTICAL, [box_sizer, None, btn_reinit_passphrase,
                          btn_change_password])

        account_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabelText', {
            lbl_email_description: N_('You are connected as:'),
            lbl_account_type_desc: N_('Account type:'),
            btn_change_offer: N_(">>> Move to a higher offer"),
            btn_disconnect: N_("Disconnect my account"),
            btn_open_bajoo_folder: N_("Open my Bajoo folder"),
            btn_reinit_passphrase: N_("Reinitialize my passphrase"),
            btn_change_password: N_("Change password")
        })


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('My Account'))
    app.SetTopWindow(win)

    tab = AccountTab(win)
    tab.set_data('email', 'sonhuytran@gmail.com')
    tab.set_data('account_type', '2GB - Free')
    tab.set_data('n_shares', 4)
    tab.set_data('quota', 2147483648)
    tab.set_data('quota_used', 894435328)

    tab.Show()
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
