# -*- coding: utf-8 -*-

import wx
from wx.lib.filebrowsebutton import DirBrowseButton

from ...common.i18n import N_

from ..base_view import BaseView
from ..form.members_share_form import MembersShareForm


class CreationShareTab(wx.Panel):
    """
    The share creation tab in the main window,
    which allows user to create a new share.
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = CreationShareView(self)


class CreationShareView(BaseView):
    """View of the creation share screen"""

    def __init__(self, creation_share_tab):
        BaseView.__init__(self, creation_share_tab)

        btn_back = wx.Button(
            creation_share_tab, label=N_('<< Back to share list'),
            name='btn_back')
        btn_cancel = wx.Button(creation_share_tab, wx.ID_CANCEL)
        btn_create = wx.Button(
            creation_share_tab, wx.ID_OK, label=N_('Create'))
        txt_share_name = wx.TextCtrl(
            creation_share_tab, name='txt_share_name')
        txt_share_name.SetHint(N_('Share name'))
        rbtn_team_share = wx.RadioButton(
            creation_share_tab,
            label=N_("Team share"), style=wx.RB_GROUP,
            name='rbtn_team_share')
        rbtn_public_share = wx.RadioButton(
            creation_share_tab, label=N_("Public share"),
            name='rbtn_public_share')
        chk_encryption = wx.CheckBox(
            creation_share_tab, label=N_("Encrypt this share"),
            name='chk_encryption')
        chk_exclusion = wx.CheckBox(
            creation_share_tab, label=N_('Do not synchronize on this PC'),
            name='chk_exclusion')
        btn_browse_location = DirBrowseButton(
            creation_share_tab, labelText=N_('Location on this PC'))

        # TODO: disable for next release
        rbtn_team_share.Disable()
        rbtn_public_share.Disable()
        chk_exclusion.Disable()
        btn_browse_location.Disable()

        # the top sizer contains the back button
        top_sizer = self.make_sizer(
            wx.HORIZONTAL, [btn_back], outside_border=False)

        # the share_info sizer contains fields
        # for share name, share type, and encryption
        share_type_sizer = self.make_sizer(
            wx.HORIZONTAL, [rbtn_team_share, rbtn_public_share],
            outside_border=False)
        share_info_sizer = self.make_sizer(
            wx.VERTICAL, [txt_share_name, share_type_sizer, chk_encryption],
            flag=wx.EXPAND, outside_border=False)

        # the members share form
        lbl_members = wx.StaticText(
            creation_share_tab,
            label=N_('Members having access to this share'))
        members_share_form = MembersShareForm(creation_share_tab)

        # the share_options sizer contains options of exclusion & local dir
        share_options_sizer = self.make_sizer(
            wx.VERTICAL, [chk_exclusion, btn_browse_location],
            flag=wx.EXPAND, outside_border=False)

        # the button sizer
        buttons_sizer = wx.StdDialogButtonSizer()
        buttons_sizer.SetAffirmativeButton(btn_create)
        buttons_sizer.SetCancelButton(btn_cancel)
        buttons_sizer.Realize()

        main_sizer = self.make_sizer(wx.VERTICAL, [top_sizer])
        main_sizer.AddMany([
            (share_info_sizer, 0, wx.EXPAND | wx.ALL, 15),
            (lbl_members, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15),
            (members_share_form, 1, wx.EXPAND | wx.ALL, 15),
            (share_options_sizer, 0, wx.EXPAND | wx.ALL, 15),
            (buttons_sizer, 0, wx.EXPAND | wx.ALL, 15)])
        creation_share_tab.SetSizer(main_sizer)


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('New Share'))
    app.SetTopWindow(win)

    tab = CreationShareTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
