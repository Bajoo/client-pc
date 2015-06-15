# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView
from . import BaseForm


class ProxyForm(BaseForm):
    """Form of the proxy configuration.

    This form don't contains any submit button.
    """
    def __init__(self, parent, **kwargs):
        BaseForm.__init__(self, parent, **kwargs)
        self._view = ProxyFormView(self)
        # TODO: implement ...


class ProxyFormView(BaseView):
    """View of the ProxyForm"""

    def __init__(self, proxy_form):
        BaseView.__init__(self, proxy_form)

        box = wx.StaticBox(proxy_form)
        self.register_i18n(proxy_form.SetLabel, N_('Proxy'))

        # Proxy type
        auto_radio = wx.RadioButton(proxy_form, style=wx.RB_GROUP,
                                    name='auto_config')
        self.register_i18n(
            auto_radio.SetLabel,
            N_('Automatic detection of proxy settings for this network.'))
        system_radio = wx.RadioButton(proxy_form, name='system_config')
        self.register_i18n(system_radio.SetLabel, N_('System settings'))
        no_radio = wx.RadioButton(proxy_form, name='no_config')
        self.register_i18n(no_radio.SetLabel, N_('Do not use proxy'))
        manual_radio = wx.RadioButton(proxy_form, name='manual_config')
        self.register_i18n(manual_radio.SetLabel, N_('Manual settings'))

        proxy_type_txt = wx.StaticText(proxy_form)
        self.register_i18n(proxy_type_txt.SetLabel, N_('Proxy type:'))
        proxy_type_choice = wx.Choice(proxy_form, name='proxy_type',
                                      choices=["HTTP", "SOCKS4", "SOCKS5"])
        proxy_type_choice.SetSelection(0)

        server_input = wx.TextCtrl(proxy_form, name='server_uri')
        port_input = wx.TextCtrl(proxy_form, name='server_port')
        auth_box = wx.CheckBox(proxy_form, name='use_auth')
        self.register_i18n(auth_box.SetLabel,
                           N_('The server requires an authentication'))

        username_input = wx.TextCtrl(proxy_form, name='username')
        password_input = wx.TextCtrl(proxy_form, style=wx.TE_PASSWORD,
                                     name='password')

        sizer_radio = wx.BoxSizer(wx.VERTICAL)
        sizer_radio.AddMany([auto_radio, system_radio, no_radio, manual_radio])

        uri_sizer = wx.BoxSizer(wx.HORIZONTAL)
        uri_sizer.Add(server_input, proportion=5, flag=wx.ALIGN_CENTER)
        uri_sizer.Add(wx.StaticText(proxy_form, label=':'),
                      flag=wx.ALIGN_CENTER | wx.RIGHT | wx.LEFT,
                      border=10)
        uri_sizer.Add(port_input, proportion=1, flag=wx.ALIGN_CENTER)

        s = self.make_sizer(wx.VERTICAL, [
            sizer_radio,
            self.make_sizer(wx.HORIZONTAL, [proxy_type_txt, proxy_type_choice],
                            outside_border=False, flag=wx.ALIGN_CENTER),
            uri_sizer,
            auth_box,
            self.make_sizer(wx.HORIZONTAL, [username_input, password_input],
                            outside_border=False, proportion=1)
        ])

        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.Add(s, flag=wx.EXPAND)

        proxy_form.SetSizer(sizer)


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
