# -*- coding: utf-8 -*-
import wx

from ...common.i18n import N_


def _show_success_message(message, caption, parent=None):
    wx.MessageBox(message, caption,
                  style=wx.OK | wx.ICON_INFORMATION,
                  parent=parent)


def _show_error_message(message, caption, parent=None):
    wx.MessageBox(message, caption,
                  style=wx.OK | wx.ICON_ERROR,
                  parent=parent)


def message_change_password_success(parent=None):
    message = N_("Your password has been changed.\n\n"
                 "You will be deconnected soon.\n"
                 "You can reconnect with your new password.")
    caption = N_("Password changed successfully.")
    _show_success_message(message, caption, parent)