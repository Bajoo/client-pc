# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class ActivationScreen(wx.Panel):
    """Ask the user to activate his account."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = ActivationScreenView(self)


class ActivationScreenView(BaseView):

    def __init__(self, activation_screen):
        BaseView.__init__(self, activation_screen)

        self.set_frame_title(N_('Bajoo - Activate your account'))

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

        sizer = self.make_sizer(wx.VERTICAL, [
            title_txt, content_txt, None,
            [come_back_later_btn, None, done_btn]])
        activation_screen.SetSizer(sizer)


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
