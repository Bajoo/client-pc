#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent

from ..common.i18n import N_, _
from .base_view import BaseView

bug_send_request, EVT_BUG_REPORT = NewCommandEvent()


class BugReportWindow(wx.Dialog):

    def __init__(self, parent=None):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        wx.Dialog.__init__(self,
                           parent,
                           wx.ID_ANY,
                           pos=wx.DefaultPosition,
                           size=wx.Size(500, 250),
                           style=style)

        self._view = BugReportView(self)
        self.Bind(wx.EVT_BUTTON, self._on_submit)

    def _on_submit(self, event):
        if event.GetId() == wx.ID_APPLY:
            value = self.FindWindow('report_txt').GetValue()

            if not value:
                dlg = wx.MessageDialog(self,
                                       _('Need bug description'),
                                       _('No message sent!'),
                                       wx.OK | wx.ICON_WARNING)
                dlg.ShowModal()
                dlg.Destroy()

                return

            bug_send_event = bug_send_request(self.GetId())
            bug_send_event.report = value
            wx.PostEvent(wx.GetApp(), bug_send_event)

        self.Show(False)
        self.Destroy()
        event.Skip()


class BugReportView(BaseView):
    """View of the BugReportWindow"""

    def __init__(self, window):
        BaseView.__init__(self, window)

        self.set_frame_title(N_('Send a message to the developers'))
        self.set_icon()

        sizer = wx.BoxSizer(wx.VERTICAL)

        pnl = wx.Panel(window)
        instruction_box = wx.StaticBox(pnl)
        self.register_i18n(
            instruction_box,
            instruction_box.SetLabel,
            N_('Write your message here: '))
        sbs = wx.StaticBoxSizer(instruction_box, orient=wx.VERTICAL)
        self.text = wx.TextCtrl(pnl, style=wx.TE_MULTILINE, name='report_txt')
        sbs.Add(self.text, 1, wx.EXPAND | wx.ALL, border=4)
        pnl.SetSizer(sbs)

        warning_label = wx.StaticText(window, style=wx.TE_MULTILINE)
        self.register_i18n(
            warning_label,
            warning_label.SetLabel,
            N_('Settings and log files will be joined to your message.'))

        btn_sizer = wx.StdDialogButtonSizer()

        cancel_button = wx.Button(window, wx.ID_CANCEL)
        btn_sizer.SetCancelButton(cancel_button)
        self.register_i18n(cancel_button, cancel_button.SetLabel, N_('Cancel'))

        send_button = wx.Button(window, wx.ID_APPLY)
        btn_sizer.SetAffirmativeButton(send_button)
        self.register_i18n(send_button, send_button.SetLabel, N_('Send'))

        btn_sizer.Realize()

        sizer.Add(pnl, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        sizer.Add(warning_label,
                  proportion=0,
                  flag=wx.ALIGN_LEFT | wx.ALL,
                  border=5)
        sizer.Add(btn_sizer, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)

        window.SetSizer(sizer)

if __name__ == '__main__':
    ex = wx.App()
    dial = BugReportWindow(None)
    dial.Show(True)

    def _fake_send_bug(event):
        print('bug report sent:')
        print(event.report)

    ex.Bind(EVT_BUG_REPORT, _fake_send_bug)

    ex.MainLoop()
