# -*- coding: utf-8 -*-
import wx

from ...common.i18n import _


def _show_confirmation_box(message, caption, parent=None):
    dialog = wx.MessageDialog(parent, message, caption,
                              style=wx.YES | wx.NO | wx.ICON_QUESTION)
    dialog.SetYesNoLabels(_("Yes"), _("No"))

    return dialog.ShowModal()


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


def message_box_members_changed(parent=None):
    """
    On the MembersShareForm, in the case where user has changed
    email/permission but hasn't committed the new value yet
    (by clicking the button +), this message box will
    ask the user to
    - leave and submit the form
    - or stay at the form to commit changes.

    Returns:
        wx.YES if the user confirms, wx.NO if he don't.
    """
    message = _("Your member setting has not been saved yet."
                "Do you want to continue and ignore the changes ?")
    caption = _("Data not saved")

    return _show_confirmation_box(message, caption, parent)


def main():
    app = wx.App()
    win = wx.Frame(None)
    message_box_delete_share("SHARE_NAME_EXAMPLE", win)
    message_box_quit_share("SHARE_NAME_EXAMPLE", win)
    message_box_members_changed(win)

if __name__ == '__main__':
    main()
