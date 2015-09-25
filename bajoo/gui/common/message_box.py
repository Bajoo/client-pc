# -*- coding: utf-8 -*-
import wx

from ...common.i18n import _


def _show_confirmation_box(message, caption, parent=None):
    return wx.MessageBox(message, caption,
                         style=wx.YES | wx.NO | wx.ICON_QUESTION,
                         parent=parent)


def message_box_delete_share(share_name, parent=None):
    """Ask the user his confirmation about deleting a sharing, in a modal box.

    Returns:
        wx.YES if the user confirms, wx.NO if he don't.
    """
    message = _("Are you sure to delete the team share %s?") % share_name
    caption = _("Delete team share")

    return _show_confirmation_box(message, caption, parent)


def message_box_quit_share(share_name, parent=None):
    """Ask the user his confirmation about leaving a sharing, in a modal box.

    Returns:
        wx.YES if the user confirms, wx.NO if he don't.
    """
    message = _("Are you sure to remove %s from your shares?") % share_name
    caption = _("Quit team share")

    return _show_confirmation_box(message, caption, parent)
