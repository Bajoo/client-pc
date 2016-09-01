#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import wx
from wx.lib.newevent import NewCommandEvent
from wx.lib.agw.hyperlink import HyperLinkCtrl

from ..common.i18n import N_, _
from .event_promise import ensure_gui_thread
from .base_view import BaseView

bug_send_request, EVT_BUG_REPORT = NewCommandEvent()


class BugReportWindow(wx.Dialog):

    def __init__(self, parent=None):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        wx.Dialog.__init__(self,
                           parent,
                           wx.ID_ANY,
                           pos=wx.DefaultPosition,
                           size=wx.Size(600, 400),
                           style=style)

        self._view = BugReportView(self)
        self.Bind(wx.EVT_BUTTON, self._on_submit)

    def _on_submit(self, event):
        if event.GetId() == wx.ID_APPLY:
            value = self.FindWindow('report_txt').GetValue()
            email = self.FindWindow('email').GetValue()

            if not value:
                self.set_error_message(_('The bug description is required'))
                return

            if not email:
                self.set_error_message(_('The email field is required'))
                return

            if not re.match('.{2,}@.{2,}', email):
                self.set_error_message(_('The email must be valid.'))
                return

            bug_send_event = bug_send_request(self.GetId())
            bug_send_event.report = value
            bug_send_event.email = email
            wx.PostEvent(wx.GetApp(), bug_send_event)

            self._view.disable_form()
        else:
            self.Destroy()
            event.Skip()

    @ensure_gui_thread
    def set_error_message(self, message):
        """Display a message to the user in response of the form submission.

        Args:
            message (str): message to display
        """
        self._view.enable_form()
        dlg = wx.MessageDialog(self,
                               message,
                               _('Error'),
                               wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()

    @ensure_gui_thread
    def display_confirmation(self):
        """Display a confirmation message, then closes the window."""
        message = _('Your message has been sent to the developers. They will'
                    ' reply to you by email.')
        dlg = wx.MessageDialog(self,
                               message,
                               _('Bug report sent!'),
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        self.Destroy()


class BugReportView(BaseView):
    """View of the BugReportWindow"""

    def __init__(self, window):
        BaseView.__init__(self, window)

        self.set_frame_title(N_('Send a message to the developers'))
        self.set_icon()

        sizer = wx.BoxSizer(wx.VERTICAL)

        caption = wx.StaticText(window)
        sizer.Add(caption, 0, wx.EXPAND | wx.ALL, border=10)
        self.register_i18n(
            caption,
            caption.SetLabel,
            N_('The configuration of your Bajoo client and its log files will '
               'be attached to your message.\n'
               'Please note that this is not a support channel and that no '
               'response will be made in this way. For inquiries, please '
               'contact support by email:'))
        caption.Wrap(580)
        email_link = HyperLinkCtrl(window)
        sizer.Add(email_link, 0, wx.EXPAND | wx.RIGHT | wx.LEFT | wx.BOTTOM,
                  border=10)
        self.register_i18n(
            email_link,
            email_link.SetLabel,
            N_('support-en@bajoo.fr'))
        self.register_i18n(
            email_link,
            email_link.SetURL,
            N_('mailto:support-en@bajoo.fr'))

        email_label = wx.StaticText(window, label=_('Email:'))
        self.email = wx.TextCtrl(window, name='email')
        sizer.Add(email_label, 0, wx.EXPAND | wx.ALL, border=4)
        sizer.Add(self.email, 0, wx.EXPAND | wx.ALL, border=4)

        text_label = wx.StaticText(window)
        self.register_i18n(
            text_label,
            text_label.SetLabel,
            N_('Write your message here: '))
        sizer.Add(text_label, 0, wx.EXPAND | wx.ALL, border=4)

        self.text = wx.TextCtrl(window, style=wx.TE_MULTILINE,
                                name='report_txt')
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, border=4)

        warning_label = wx.StaticText(window, style=wx.TE_MULTILINE)
        self.register_i18n(
            warning_label,
            warning_label.SetLabel,
            N_('Settings and log files will be joined to your message.'))

        btn_sizer = wx.StdDialogButtonSizer()

        self.cancel_button = cancel_button = wx.Button(window, wx.ID_CANCEL)
        btn_sizer.SetCancelButton(cancel_button)
        self.register_i18n(cancel_button, cancel_button.SetLabel, N_('Cancel'))

        self.send_button = send_button = wx.Button(window, wx.ID_APPLY)
        btn_sizer.SetAffirmativeButton(send_button)
        self.register_i18n(send_button, send_button.SetLabel, N_('Send'))

        btn_sizer.Realize()

        sizer.Add(warning_label,
                  proportion=0,
                  flag=wx.ALIGN_LEFT | wx.ALL,
                  border=5)
        sizer.Add(btn_sizer, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)

        window.SetSizer(sizer)

    def disable_form(self):
        self.email.Disable()
        self.text.Disable()
        self.cancel_button.Disable()
        self.send_button.Disable()

    def enable_form(self):
        self.email.Enable()
        self.text.Enable()
        self.cancel_button.Enable()
        self.send_button.Enable()


if __name__ == '__main__':
    ex = wx.App()
    dial = BugReportWindow(None)
    dial.Show(True)

    def _fake_send_bug(event):
        print('bug report sent:')
        print(event.report)
        dial.display_confirmation()

    ex.Bind(EVT_BUG_REPORT, _fake_send_bug)

    ex.MainLoop()
