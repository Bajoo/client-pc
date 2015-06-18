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
                  self.FindWindowByName('use_auth'))

    def populate(self):
        mode = config.get('proxy_mode')
        proxy_type = config.get('proxy_type')
        url = config.get('proxy_url') or ''
        port = config.get('proxy_port') or ''
        user = config.get('proxy_user') or ''
        password = config.get('proxy_password') or ''

        mode_radio = self.FindWindowByName(mode)
        if mode_radio:
            mode_radio.SetValue(True)
        else:
            self.FindWindowByName('system_settings').SetValue(True)

        try:
            selection = self.proxy_type_list.index(proxy_type)
        except ValueError:
            selection = 0
        self.FindWindowByName('proxy_type').SetSelection(selection)

        self.FindWindowByName('server_uri').SetValue(url)
        self.FindWindowByName('server_port').SetValue(port)
        self.FindWindowByName('username').SetValue(user)
        self.FindWindowByName('password').SetValue(password)

    def apply_field_constraints(self, _evt=None):
        """Set the form in a coherent state by applying fields constraints.

        Note: it takes an ignored argument (optional), so it can be used has
        an event handler.
        """

        is_manual_config = self.FindWindowByName('manual_settings').GetValue()
        use_auth = self.FindWindowByName('use_auth').GetValue()

        for name in ('proxy_type', 'server_uri', 'server_port', 'use_auth'):
            self.FindWindowByName(name).Enable(is_manual_config)

        for name in ('username', 'password'):
            self.FindWindowByName(name).Enable(is_manual_config and use_auth)

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
        return data


class ProxyFormView(BaseView):
    """View of the ProxyForm"""

    def create_children(self):
        """Create all named children of proxy form."""

        system_radio = wx.RadioButton(self.window, name='system_settings',
                                      style=wx.RB_GROUP)
        self.register_i18n(system_radio.SetLabel, N_('System settings'))
        no_radio = wx.RadioButton(self.window, name='no_proxy')
        self.register_i18n(no_radio.SetLabel, N_('Do not use proxy'))
        manual_radio = wx.RadioButton(self.window, name='manual_settings')
        self.register_i18n(manual_radio.SetLabel, N_('Manual settings'))

        wx.Choice(self.window, name='proxy_type',
                  choices=["HTTP", "SOCKS4", "SOCKS5"])

        server_uri_txt = wx.TextCtrl(self.window, name='server_uri')
        server_port_txt = wx.TextCtrl(self.window, name='server_port')
        self.register_i18n(server_uri_txt.SetHint, N_('Server'))
        self.register_i18n(server_port_txt.SetHint, N_('Port'))

        auth_box = wx.CheckBox(self.window, name='use_auth')
        self.register_i18n(auth_box.SetLabel,
                           N_('The server requires an authentication'))
        username_txt = wx.TextCtrl(self.window, name='username')
        password_txt = wx.TextCtrl(self.window, style=wx.TE_PASSWORD,
                                   name='password')
        self.register_i18n(username_txt.SetHint, N_('User'))
        self.register_i18n(password_txt.SetHint, N_('Password'))

    def create_layout(self):
        """Create appropriate layout and static text for proxy form."""

        proxy_type_txt = wx.StaticText(self.window)
        self.register_i18n(proxy_type_txt.SetLabel, N_('Proxy type:'))

        sizer_radio = wx.BoxSizer(wx.VERTICAL)
        sizer_radio.AddMany([
            self.window.FindWindowByName('system_settings'),
            self.window.FindWindowByName('no_proxy'),
            self.window.FindWindowByName('manual_settings')
        ])

        # Line "[ server_uri ] : [ server_port ]"
        uri_sizer = wx.BoxSizer(wx.HORIZONTAL)
        uri_sizer.Add(self.window.FindWindowByName('server_uri'),
                      proportion=5, flag=wx.ALIGN_CENTER)
        uri_sizer.Add(wx.StaticText(self.window, label=':'),
                      flag=wx.ALIGN_CENTER | wx.RIGHT | wx.LEFT, border=10)
        uri_sizer.Add(self.window.FindWindowByName('server_port'),
                      proportion=1, flag=wx.ALIGN_CENTER)

        s = self.make_sizer(wx.VERTICAL, [
            sizer_radio,
            self.make_sizer(wx.HORIZONTAL, [
                proxy_type_txt,
                self.window.FindWindowByName('proxy_type')
            ], outside_border=False, flag=wx.ALIGN_CENTER),
            uri_sizer,
            self.window.FindWindowByName('use_auth'),
            self.make_sizer(wx.HORIZONTAL, [
                self.window.FindWindowByName('username'),
                self.window.FindWindowByName('password')
            ], outside_border=False, proportion=1)
        ])

        box = wx.StaticBox(self.window)
        self.register_i18n(self.window.SetLabel, N_('Proxy'))
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
