# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..translator import Translator


class ActivationScreen(wx.Panel):
    """Ask the user to activate his account."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = ActivationScreenView(self)


class ActivationScreenView(Translator):

    def __init__(self, activation_screen):
        Translator.__init__(self)

        self.register_i18n(activation_screen.GetTopLevelParent().SetTitle,
                           N_('Bajoo - Activate your account'))

        title_txt = wx.StaticText(activation_screen)
        title_txt.SetFont(title_txt.GetFont().Bold())
        self.register_i18n(title_txt.SetLabel,
                           N_('Your account is not activated.'))
        content_txt = wx.StaticText(activation_screen)
        self.register_i18n(content_txt.SetLabel, N_(
            "For continuing, your must activate your account.\n"
            "You should receive in the next minutes, a confirmation email with"
            " an activation link.\n"
            "You should follow that link to continue."
        ))

        # TODO: disable the form after it's submitted.
        come_back_later_btn = wx.Button(activation_screen)
        self.register_i18n(come_back_later_btn.SetLabel, N_('Come back later'))
        done_btn = wx.Button(activation_screen)
        self.register_i18n(done_btn.SetLabel, N_("It's done!"))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(title_txt, flag=wx.ALL, border=15)
        main_sizer.Add(content_txt, flag=wx.RIGHT | wx.LEFT | wx.BOTTOM,
                       border=15)
        main_sizer.AddStretchSpacer()

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(come_back_later_btn)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(done_btn)
        main_sizer.Add(button_sizer,
                       flag=wx.RIGHT | wx.LEFT | wx.BOTTOM | wx.EXPAND,
                       border=15)

        activation_screen.SetSizer(main_sizer)


def main():
    from ...common import config
    config.load()
    app = wx.App()
    win = wx.Frame(None)
    app.SetTopWindow(win)
    screen = ActivationScreen(win)
    screen.GetSizer().SetSizeHints(win)
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
