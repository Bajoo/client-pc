# -*- coding: utf-8 -*-

import wx
from wx.lib.agw.hyperlink import HyperLinkCtrl

from ...common.i18n import N_
from ..base_view import BaseView


class AccountTab(wx.Panel):
    """
    Account settings tab in the main window, which allows user to:
    * view account information like email, quota
    * change password
    * change offer plan
    * reset encryption passphrase
    * disconnect
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = AccountView(self)
        self._data = {
            'email': '',
            'account_type': '',
            'n_shares': 0,
            'quota': 0,
            'quota_used': 0
        }

    def set_data(self, key, value):
        self._data[key] = value

    def _populate(self):
        quota_percentage = 0

        # TODO: human readable size
        if 'quota' in self._data.keys() \
                and 'quota_used' in self._data.keys():
            quota_percentage = \
                self._data['quota_used'] * 100 / float(self._data['quota'])
            print(quota_percentage)

        self.FindWindow('lbl_email').SetLabelText(
            N_("You are connected as") + " " + self._data['email'])
        self.FindWindow('lbl_account_type').SetLabelText(
            N_("Account type:") + " " + self._data['account_type'])
        self.FindWindow('lbl_quota_info').SetLabelText(
            str(self._data['n_shares']) + " " + N_("share folder use")
            + " " + str(self._data['quota_used']) + ", "
            + (N_("so %0.2f%% of your Bajoo storage.") % quota_percentage))
        self.FindWindow('gauge_quota') \
            .SetValue(quota_percentage)
        self.FindWindow('gauge_text_min') \
            .SetLabelText('0')
        self.FindWindow('gauge_text_value') \
            .SetLabelText(str(self._data['quota_used']))
        self.FindWindow('gauge_text_max') \
            .SetLabelText(str(self._data['quota']))

    def Show(self, show=True):
        self._populate()
        wx.Panel.Show(self, show)


class AccountView(BaseView):
    """View of the account screen"""

    def __init__(self, account_screen):
        BaseView.__init__(self, account_screen)

        account_info_box = wx.StaticBox(account_screen, -1)
        box_sizer = wx.StaticBoxSizer(account_info_box, wx.VERTICAL)

        # lbl_email
        lbl_email = wx.StaticText(
            account_screen, wx.ID_ANY,
            N_("You are connected as"), name='lbl_email')

        # lbl_account_type
        lbl_account_type = wx.StaticText(
            account_screen, wx.ID_ANY,
            N_("Account type:"), name='lbl_account_type')

        # btn_change_offer
        # TODO: URL
        btn_change_offer = HyperLinkCtrl(
            account_screen, wx.ID_ANY,
            N_(">>> Move to a higher offer"),
            URL="https://www.bajoo.fr",
            name='btn_change_offer')

        # lbl_quota_info
        lbl_quota_info = wx.StaticText(
            account_screen, wx.ID_ANY,
            "quota_info", name='lbl_quota_info')

        # btn_disconnect
        btn_disconnect = wx.Button(
            account_screen, wx.ID_ANY,
            N_("Disconnect my account"),
            name='btn_disconnect')

        # btn_open_bajoo_folder
        btn_open_bajoo_folder = wx.Button(
            account_screen, wx.ID_ANY,
            N_("Open my Bajoo folder"),
            name='btn_open_bajoo_folder')

        # btn_reinit_passphrase
        btn_reinit_passphrase = wx.Button(
            account_screen, wx.ID_ANY,
            N_("Reinitialize my passphrase"),
            name='btn_reinit_passphrase')
        btn_reinit_passphrase.SetMinSize(
            (200, btn_reinit_passphrase.GetSize()[1]))

        # btn_change_password
        btn_change_password = wx.Button(
            account_screen, wx.ID_ANY,
            N_("Change password"),
            name='btn_change_password')
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
        info_text_sizer.Add(lbl_email)
        info_text_sizer.Add(lbl_account_type, 0, wx.TOP, 10)
        info_text_sizer.Add(btn_change_offer, 0, wx.TOP, 10)
        info_text_sizer.Add(lbl_quota_info, 0, wx.TOP, 10)

        info_button_sizer = wx.BoxSizer(wx.VERTICAL)
        info_button_sizer.Add(btn_disconnect, 0, wx.EXPAND | wx.RIGHT, 0)
        info_button_sizer.Add(btn_open_bajoo_folder, 0,
                              wx.EXPAND | wx.TOP, 10)

        info_text_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        info_text_button_sizer.Add(info_text_sizer)
        info_text_button_sizer.AddStretchSpacer(1)
        info_text_button_sizer.Add(info_button_sizer, 0, wx.LEFT, 10)

        gauge_text_sizer = wx.BoxSizer(wx.HORIZONTAL)
        gauge_text_sizer.Add(gauge_text_min)
        gauge_text_sizer.AddStretchSpacer()
        gauge_text_sizer.Add(gauge_text_value)
        gauge_text_sizer.AddStretchSpacer()
        gauge_text_sizer.Add(gauge_text_max)

        box_sizer.Add(info_text_button_sizer, 1, wx.EXPAND | wx.ALL, 10)
        box_sizer.Add(gauge_quota, 0,
                      wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        box_sizer.Add(gauge_text_sizer, 0,
                      wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(box_sizer, 0,
                       wx.EXPAND | wx.LEFT | wx.TOP | wx.RIGHT, 10)
        main_sizer.AddStretchSpacer()
        main_sizer.Add(btn_reinit_passphrase, 0,
                       wx.LEFT | wx.TOP, 10)
        main_sizer.Add(btn_change_password, 0,
                       wx.LEFT | wx.TOP | wx.BOTTOM, 10)

        account_screen.SetSizer(main_sizer)


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
