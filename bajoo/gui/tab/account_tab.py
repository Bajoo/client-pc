# -*- coding: utf-8 -*-
import logging

import wx
from wx.lib.newevent import NewCommandEvent
from wx.lib.agw.hyperlink import HyperLinkCtrl

from ...common.i18n import N_
from ...common.util import human_readable_bytes
from ..base_view import BaseView
from ...common.util import open_folder
from ..windows.change_password_window import ChangePasswordWindow
from ..translator import Translator

_logger = logging.getLogger(__name__)


class AccountTab(wx.Panel, Translator):
    """
    Account settings tab in the main window, which allows user to:
    * view account information like email, quota
    * change password
    * change offer plan
    * reset encryption passphrase
    * disconnect
    """

    DataRequestEvent, EVT_DATA_REQUEST = NewCommandEvent()
    DisconnectEvent, EVT_DISCONNECT_REQUEST = NewCommandEvent()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        Translator.__init__(self)
        self._view = AccountView(self)
        self._change_password_window = None
        self._data = {
            'email': '',
            'account_type': '',
            'n_shares': 0,
            'quota': 1,
            'quota_used': 0
        }

        # TODO: disable for next release
        self.Bind(wx.EVT_BUTTON, self._btn_disconnect,
                  self.FindWindow('btn_disconnect'))
        self.FindWindow('btn_reinit_passphrase').Disable()

        self.Bind(wx.EVT_BUTTON, self._on_open_bajoo_folder,
                  self.FindWindow('btn_open_bajoo_folder'))
        self.Bind(wx.EVT_BUTTON, self._btn_change_password_clicked,
                  self.FindWindow('btn_change_password'))

    def set_data(self, key, value):
        self._data[key] = value

    def populate(self):
        quota_str = human_readable_bytes(self._data['quota'])
        quota_used_str = human_readable_bytes(self._data['quota_used'])
        quota_percentage = 0

        if 'quota' in self._data.keys() \
                and 'quota_used' in self._data.keys():
            quota_percentage = \
                self._data['quota_used'] * 100 / float(self._data['quota'])

        if quota_percentage > 100:
            quota_percentage = 100

        self.FindWindow('lbl_email') \
            .SetLabelText(self._data['email'])
        self.FindWindow('lbl_account_type') \
            .SetLabelText('%s - %s' % (self._data['account_type'], quota_str))

        is_best_account_type = self._data.get('is_best_account_type', True)
        self.FindWindow('btn_change_offer').Show(
            not is_best_account_type)

        # re-register quota info text
        lbl_quota_info = self.FindWindow('lbl_quota_info')
        self._view.register_i18n(
            lbl_quota_info,
            lbl_quota_info.SetLabel,
            N_("%(name)d share folders use %(quota)s, so %(percent)0.2f%% "
               "of your Bajoo storage."),
            {"name": self._data['n_shares'],
             "quota": quota_used_str,
             "percent": quota_percentage})

        self.FindWindow('gauge_quota').SetValue(quota_percentage)
        self.FindWindow('gauge_text_min').SetLabelText('0')
        self.FindWindow('gauge_text_value').SetLabelText(quota_used_str)
        self.FindWindow('gauge_text_max').SetLabelText(quota_str)

    def _on_open_bajoo_folder(self, _event):
        open_folder(wx.GetApp().user_profile.root_folder_path)

    def _btn_change_password_clicked(self, _event):
        self.show_change_password_window()

    def _btn_disconnect(self, _event):
        event = AccountTab.DisconnectEvent(self.GetId())
        wx.PostEvent(self, event)

    def Show(self, show=True):
        self.FindWindow('lbl_message').Hide()
        self.Layout()
        event = AccountTab.DataRequestEvent(self.GetId())
        wx.PostEvent(self, event)

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self.populate()
        self._view.notify_lang_change()

        if self._change_password_window is not None:
            self._change_password_window.notify_lang_change()

    def show_change_password_window(self):
        if self._change_password_window is None:
            self._change_password_window = ChangePasswordWindow(wx.GetApp(),
                                                                self)
            self._change_password_window.password_changed.connect(
                self.on_password_change_success)
            self._change_password_window.destroyed.connect(
                self.on_change_password_window_destroyed)

        # Note: show_modal() is blocking (on wxPython)
        self._change_password_window.show_modal()

    def on_change_password_window_destroyed(self):
        self._change_password_window = None

    def on_password_change_success(self):
        self.FindWindow('lbl_message').Show()
        self.Layout()


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
        btn_change_offer.Hide()

        # See bug http://trac.wxwidgets.org/ticket/17145
        bg_color = account_screen.GetBackgroundColour()
        btn_change_offer.SetBackgroundColour(bg_color)

        # TODO: set proper quota text + i18n support
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

        # lbl_message
        lbl_message = wx.StaticText(
            account_screen, name='lbl_message')
        lbl_message.SetForegroundColour(wx.BLUE)

        # btn_change_password
        btn_change_password = wx.Button(
            account_screen, name='btn_change_password')
        btn_change_password.SetMinSize(
            (200, btn_change_password.GetSize()[1]))

        # gauge_quota
        gauge_quota = wx.Gauge(
            account_screen, wx.ID_ANY, 100,
            name='gauge_quota')

        # TODO: set proper quota text + i18n support
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
            wx.VERTICAL, [box_sizer, None, lbl_message, None,
                          btn_reinit_passphrase, btn_change_password])

        account_screen.SetSizer(main_sizer)

        self.register_many_i18n('SetLabel', {
            lbl_email_description: N_('You are connected as:'),
            lbl_account_type_desc: N_('Account type:'),
            lbl_message: N_('Your password '
                            'has been successfully changed.'),
            btn_change_offer: N_(">>> Move to a upper offer"),
            btn_disconnect: N_("Disconnect my account"),
            btn_open_bajoo_folder: N_("Open my Bajoo folder"),
            btn_reinit_passphrase: N_("Reinitialize my passphrase"),
            btn_change_password: N_("Change password")
        })

    def notify_lang_change(self):
        Translator.notify_lang_change(self)


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
