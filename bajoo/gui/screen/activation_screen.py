# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView
from ..form import BaseForm


class ActivationScreen(wx.Panel):
    """Ask the user to activate his account.

    The window contains three named children: 'come_back_btn', 'done_btn'
    and 'form'

    Attributes:
        EVT_ACTIVATION_DONE (Event Id): event emitted when the user indicates
            to have activated his account.
        EVT_ACTIVATION_DELAYED (Event Id): event emitted when the user
            indicates he will not activate his account soon.
        EVT_RESEND_CONFIRM_EMAIL(Event Id): event emitted when the user
            want to receive again the activation email. The event contains an
            attribute `user_email`.

        user_email (Text): email of the user we wait the activation. It's set
            by the parent class at construction.
    """

    ActivationDoneEvent, EVT_ACTIVATION_DONE = NewCommandEvent()
    ActivationDelayedEvent, EVT_ACTIVATION_DELAYED = NewCommandEvent()
    ResendConfirmEmailEvent, EVT_RESEND_CONFIRM_EMAIL = NewCommandEvent()

    def __init__(self, parent):
        self.user_email = None

        wx.Panel.__init__(self, parent)
        self._view = ActivationScreenView(self)

        self.Bind(wx.EVT_BUTTON, self._send_delayed_event,
                  source=self.FindWindow('come_back_btn'))
        self.Bind(wx.EVT_BUTTON, self._send_resend_email_event,
                  source=self.FindWindow('resend_email_btn'))
        self.Bind(wx.EVT_BUTTON, self._send_done_event,
                  source=self.FindWindow('done_btn'))

    def _send_done_event(self, _event):
        self.FindWindow('form').disable()
        wx.PostEvent(self, self.ActivationDoneEvent(self.GetId()))

    def _send_resend_email_event(self, _event):
        self.FindWindow('resend_email_btn').Disable()
        event = self.ResendConfirmEmailEvent(self.GetId())
        event.user_email = self.user_email
        wx.PostEvent(self, event)

    def _send_delayed_event(self, _event):
        wx.PostEvent(self, self.ActivationDelayedEvent(self.GetId()))

    def reset_form(self):
        """Re-enable the form, if needed."""
        self.FindWindow('form').enable()

    def notify_lang_change(self):
        self._view.notify_lang_change()


class ActivationScreenView(BaseView):

    def __init__(self, activation_screen):
        BaseView.__init__(self, activation_screen)

        self.set_frame_title(N_('Bajoo - Activate your account'))

        title_txt = wx.StaticText(activation_screen)
        title_txt.SetFont(title_txt.GetFont().Bold())
        content_txt = wx.StaticText(activation_screen)

        form = BaseForm(activation_screen, name='form')
        come_back_later_btn = wx.Button(form, name='come_back_btn')
        resend_email_btn = wx.Button(form, name='resend_email_btn')
        done_btn = wx.Button(form, name='done_btn')
        form_sizer = self.make_sizer(wx.HORIZONTAL, [
            come_back_later_btn, None, resend_email_btn, None, done_btn],
                                     outside_border=False)
        form.SetSizer(form_sizer)

        self.register_many_i18n('SetLabel', {
            title_txt: N_('Your account is not activated.'),
            content_txt: N_(
                "For continuing, your must activate your account.\n"
                "You should receive in the next minutes, a confirmation email"
                " with an activation link.\n"
                "You should follow that link to continue."
            ),
            come_back_later_btn: N_('Come back later'),
            resend_email_btn: N_("Send confirmation email again"),
            done_btn: N_("It's done!")
        })

        sizer = self.make_sizer(wx.VERTICAL,
                                [title_txt, content_txt, None, form],
                                flag=wx.EXPAND)
        activation_screen.SetSizer(sizer)


def main():
    from ...common import config
    config.load()
    app = wx.App()
    win = wx.Frame(None)
    app.SetTopWindow(win)
    screen = ActivationScreen(win)
    screen.GetSizer().SetSizeHints(win)

    def on_activation_delayed(_evt):
        print('Activation delayed')

    def on_activation_done(_evt):
        print('Activation done')

    screen.Bind(ActivationScreen.EVT_ACTIVATION_DELAYED, on_activation_delayed)
    screen.Bind(ActivationScreen.EVT_ACTIVATION_DONE, on_activation_done)

    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
