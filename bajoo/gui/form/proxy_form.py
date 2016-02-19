# -*- coding: utf-8 -*-

import wx

from ...common import config
from ...common.i18n import N_
from ..base_view import BaseView
from . import BaseForm


class ProxyForm(BaseForm):
    """Form of the proxy configuration.

    This form contains the following named window:
    * system_settings (wx.Radio)
    * no_proxy (wx.Radio)
    * manual_settings (wx.Radio)
    * proxy_type (wx.Choice): selection can be 0 (HTTP), 1 (SOCKS4) or
        2 (SOCKS5).
    * server_uri (wx.TextCtrl)
    * server_port (wx.TextCtrl)
    * use_auth (wx.Checkbox): If checked, the "username" and "password" fields
        must be used has authentication credentials.
    * username (wx.TextCtrl)
    * password (wx.TextCtrl)

    This form don't contains any submit button. The submission of te form must
    be done outside (either manually, or by a parent form).
    """

    proxy_type_list = ['HTTP', 'SOCKS4', 'SOCKS5']

    def __init__(self, parent, **kwargs):
        BaseForm.__init__(self, parent, **kwargs)
        self._view = ProxyFormView(self)

        self._view.create_children()
        self._view.create_layout()
        self.populate()
        self.apply_field_constraints()

        self.Bind(wx.EVT_RADIOBUTTON, self.apply_field_constraints)
        self.Bind(wx.EVT_CHECKBOX, self.apply_field_constraints,
                  self.FindWindow('use_auth'))

    def populate(self):
        mode = config.get('proxy_mode')
        proxy_type = config.get('proxy_type')
        url = config.get('proxy_url') or ''
        port = config.get('proxy_port') or ''
        user = config.get('proxy_user') or ''
        password = config.get('proxy_password') or ''

        mode_radio = self.FindWindow(mode)
        if mode_radio:
            mode_radio.SetValue(True)
        else:
            self.FindWindow('system_settings').SetValue(True)

        try:
            selection = self.proxy_type_list.index(proxy_type)
        except ValueError:
            selection = 0
        self.FindWindow('proxy_type').SetSelection(selection)

        self.FindWindow('server_uri').SetValue(url or '')
        self.FindWindow('server_port').SetValue(str(port) or '0')
        self.FindWindow('username').SetValue(user or '')
        self.FindWindow('password').SetValue(password or '')
        self.FindWindow('use_auth').SetValue(
            len(user) > 0 or len(password) > 0)

    def apply_field_constraints(self, _evt=None):
        """Set the form in a coherent state by applying fields constraints.

        Note: it takes an ignored argument (optional), so it can be used has
        an event handler.
        """

        is_manual_config = self.FindWindow('manual_settings').GetValue()
        use_auth = self.FindWindow('use_auth').GetValue()

        for name in ('proxy_type', 'server_uri', 'server_port', 'use_auth'):
            self.FindWindow(name).Enable(is_manual_config)

        for name in ('username', 'password'):
            self.FindWindow(name).Enable(is_manual_config and use_auth)

    def get_data(self):
        """Override get_data to provides more easily usable results.

        `proxy_type` contains the appropriate str value.
        All `XX_settings` values are replaced by `proxy_mode`, containing
        the textual mode according to the config choices.

        Returns:
            dict
        """
        data = BaseForm.get_data(self)
        proxy_type = self.proxy_type_list[data['proxy_type']]

        proxy_mode = None
        for mode in ('system_settings', 'no_proxy', 'manual_settings'):
            if data[mode]:
                proxy_mode = mode
            del data[mode]
        data.update(proxy_type=proxy_type, proxy_mode=proxy_mode)

        use_auth = self.FindWindow('use_auth').GetValue()

        if not use_auth:
            del data['username']
            del data['password']

        return data

    def notify_lang_change(self):
        BaseForm.notify_lang_change(self)
        self._view.notify_lang_change()


class ProxyFormView(BaseView):
    """View of the ProxyForm"""

    def create_children(self):
        """Create all named children of proxy form."""

        system_radio = wx.RadioButton(self.window, name='system_settings',
                                      style=wx.RB_GROUP)
        no_radio = wx.RadioButton(self.window, name='no_proxy')
        manual_radio = wx.RadioButton(self.window, name='manual_settings')

        wx.Choice(self.window, name='proxy_type',
                  choices=["HTTP", "SOCKS4", "SOCKS5"])

        server_uri_txt = wx.TextCtrl(self.window, name='server_uri')
        server_port_txt = wx.TextCtrl(self.window, name='server_port')

        auth_box = wx.CheckBox(self.window, name='use_auth')
        username_txt = wx.TextCtrl(self.window, name='username')
        password_txt = wx.TextCtrl(self.window, style=wx.TE_PASSWORD,
                                   name='password')

        self.register_many_i18n('SetLabel', {
            system_radio: N_('System settings'),
            no_radio: N_('Do not use proxy'),
            manual_radio: N_('Manual settings'),
            auth_box: N_('The server requires an authentication')
        })

        self.register_many_i18n('SetHint', {
            server_uri_txt: N_('Server'),
            server_port_txt: N_('Port'),
            username_txt: N_('User'),
            password_txt: N_('Password')
        })

    def create_layout(self):
        """Create appropriate layout and static text for proxy form."""

        proxy_type_txt = wx.StaticText(self.window)
        self.register_i18n(proxy_type_txt,
                           proxy_type_txt.SetLabel,
                           N_('Proxy type:'))

        sizer_radio = wx.BoxSizer(wx.VERTICAL)
        sizer_radio.AddMany([
            (self.window.FindWindow('system_settings'), 0, wx.EXPAND),
            (self.window.FindWindow('no_proxy'), 0, wx.EXPAND | wx.TOP, 15),
            (self.window.FindWindow('manual_settings'),
             0, wx.EXPAND | wx.TOP, 15)
        ])

        # Line "[ server_uri ] : [ server_port ]"
        uri_sizer = wx.BoxSizer(wx.HORIZONTAL)
        uri_sizer.Add(self.window.FindWindow('server_uri'),
                      proportion=5, flag=wx.ALIGN_CENTER)
        uri_sizer.Add(wx.StaticText(self.window, label=':'),
                      flag=wx.ALIGN_CENTER | wx.RIGHT | wx.LEFT, border=10)
        uri_sizer.Add(self.window.FindWindow('server_port'),
                      proportion=1, flag=wx.ALIGN_CENTER)

        s = self.make_sizer(wx.VERTICAL, [
            sizer_radio,
            self.make_sizer(wx.HORIZONTAL, [
                proxy_type_txt,
                self.window.FindWindow('proxy_type')
            ], outside_border=False, flag=wx.ALIGN_CENTER),
            uri_sizer,
            self.window.FindWindow('use_auth'),
            self.make_sizer(wx.HORIZONTAL, [
                self.window.FindWindow('username'),
                self.window.FindWindow('password')
            ], outside_border=False, proportion=1)
        ])

        box = wx.StaticBox(self.window)
        self.register_i18n(box, box.SetLabel, N_('Proxy'))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(s, flag=wx.EXPAND)
        self.window.SetSizer(sizer)


def main():
    app = wx.App()
    win = wx.Frame(None, title='Proxy Form')
    app.SetTopWindow(win)

    form = ProxyForm(win)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(form, proportion=1, flag=wx.ALL | wx.EXPAND, border=15)
    win.SetSizer(sizer)
    sizer.SetSizeHints(win)
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
