# -*- coding: utf-8 -*-
import wx

from ...common.i18n import N_


def _show_success_message(message, caption, parent=None):
    return wx.MessageBox(message, caption,
                         style=wx.OK | wx.ICON_INFORMATION,
                         parent=parent)


def _show_error_message(message, caption, parent=None):
    return wx.MessageBox(message, caption,
                         style=wx.OK | wx.ICON_ERROR,
                         parent=parent)


def _show_confirmation_box(message, caption, parent=None):
    return wx.MessageBox(message, caption,
                         style=wx.YES | wx.NO | wx.ICON_QUESTION,
                         parent=parent)


def message_change_password_success(parent=None):
    message = N_("Your password has been changed.\n\n"
                 "You will be deconnected soon.\n"
                 "You can reconnect with your new password.")
    caption = N_("Password changed successfully.")

    return _show_success_message(message, caption, parent)


def message_delete_share(share_name, parent=None):
    message = N_("Are you sure to delete the team share %s?" % share_name)
    caption = N_("Delete team share")

    return _show_confirmation_box(message, caption, parent)


def message_quit_share(share_name, parent=None):
    message = N_("Are you sure to remove %s from your shares?" % share_name)
    caption = N_("Quit team share")

    return _show_confirmation_box(message, caption, parent)
