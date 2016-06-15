# -*- coding: utf-8 -*-

from os import path

import wx
from wx.lib.newevent import NewCommandEvent

from ...api.team_share import permission as share_permission
from ...common.i18n import N_, _
from ..common import message_box
from ..common.pictos import get_bitmap
from ..common.share_location_browser import ShareLocationBrowser
from ..base_view import BaseView
from ..form.members_share_form import MembersShareForm
from ..form.base_form import BaseForm


class CreationShareTab(BaseForm):
    """
    The share creation tab in the main window,
    which allows user to create a new share.
    """

    RequestCreateShareEvent, EVT_CREATE_SHARE_REQUEST = NewCommandEvent()
    RequestShowListShares, EVT_SHOW_LIST_SHARE_REQUEST = NewCommandEvent()

    def __init__(self, parent):
        BaseForm.__init__(self, parent)
        self._init_images()
        self._view = CreationShareView(self)
        self._user_email = ''
        self.members = {}

        self.Bind(wx.EVT_TEXT, self._share_name_changed,
                  self.FindWindow('txt_share_name'))
        self.Bind(wx.EVT_BUTTON, self._btn_create_clicked, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._btn_back_clicked,
                  self.FindWindow('btn_back'))
        self.Bind(wx.EVT_BUTTON, self._btn_back_clicked, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CHECKBOX, self._chk_exclusion_checked,
                  self.FindWindow('chk_exclusion'))
        self.Bind(MembersShareForm.EVT_SUBMIT, self._on_add_member)

        self._user_email = wx.GetApp()._user.name
        self._view.members_share_form.excluded_emails.append(self._user_email)

    def _init_images(self):
        self.IMG_MEMBERS = get_bitmap('group.png', False)
        self.IMG_BACK = get_bitmap('previous.png', False)

    def _share_name_changed(self, event):
        share_name = event.GetEventObject().GetValue()
        btn_browse_location = self.FindWindow('btn_browse_location')
        btn_browse_location.set_share_name(share_name)

    def _btn_back_clicked(self, _event):
        back_event = CreationShareTab.RequestShowListShares(self.GetId())
        wx.PostEvent(self, back_event)

    def _btn_create_clicked(self, event):
        if self._view.members_share_form.has_changes:
            confirm = message_box.message_box_members_changed(self)

            if confirm != wx.ID_YES:
                return

        share_name = self.FindWindow('txt_share_name').GetValue()

        if share_name:
            request_event = CreationShareTab.RequestCreateShareEvent(
                self.GetId())
            request_event.share_name = share_name
            request_event.encrypted = \
                self.FindWindow('chk_encryption').GetValue()
            request_event.members = self.members
            request_event.do_not_sync = \
                self.FindWindow('chk_exclusion').GetValue()
            request_event.path = None

            if not request_event.do_not_sync:
                request_event.path = \
                    self.FindWindow('btn_browse_location').GetValue()

            wx.PostEvent(self, request_event)
            self.disable()

    def _chk_exclusion_checked(self, event):
        do_not_sync = self.FindWindow('chk_exclusion').GetValue()
        self.FindWindow('btn_browse_location').Enable(not do_not_sync)

    def _on_add_member(self, event):
        # Retrieve the event data
        email = event.user_email
        permission_name = event.permission

        # Create a new member object
        member_object = dict(share_permission[permission_name])
        member_object['user'] = email

        # Update the member and reload the members form
        self.members[email] = member_object
        self._view.members_share_form.load_members(self.members.values())

    def notify_lang_change(self):
        BaseForm.notify_lang_change(self)
        self._view.notify_lang_change()


class CreationShareView(BaseView):
    """View of the creation share screen"""

    def __init__(self, creation_share_tab):
        BaseView.__init__(self, creation_share_tab)

        btn_back = wx.BitmapButton(
            creation_share_tab, name='btn_back',
            bitmap=creation_share_tab.IMG_BACK)
        btn_cancel = wx.Button(creation_share_tab, wx.ID_CANCEL)
        btn_create = wx.Button(creation_share_tab, wx.ID_OK)
        txt_share_name = wx.TextCtrl(creation_share_tab, name='txt_share_name')
        rbtn_team_share = wx.RadioButton(
            creation_share_tab, style=wx.RB_GROUP, name='rbtn_team_share')
        rbtn_public_share = wx.RadioButton(
            creation_share_tab, name='rbtn_public_share')
        chk_encryption = wx.CheckBox(
            creation_share_tab, name='chk_encryption')
        chk_encryption.SetValue(True)
        chk_exclusion = wx.CheckBox(
            creation_share_tab, name='chk_exclusion')

        share_folder = path.join(
            wx.GetApp().user_profile.root_folder_path, _('Shares'))
        btn_browse_location = ShareLocationBrowser(
            parent=creation_share_tab, name='btn_browse_location',
            startDirectory=share_folder)
        btn_browse_location.SetValue(share_folder)

        # TODO: disable for next release
        rbtn_team_share.Disable()
        rbtn_public_share.Disable()

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
        img_members = wx.StaticBitmap(
            creation_share_tab, label=creation_share_tab.IMG_MEMBERS,
            name='img_members')
        lbl_members = wx.StaticText(creation_share_tab, name='lbl_members')
        lbl_members_box = self.make_sizer(
            wx.HORIZONTAL, [img_members, lbl_members],
            outside_border=False, flag=wx.ALIGN_CENTER)
        self.members_share_form = MembersShareForm(creation_share_tab)
        creation_share_tab.members_share_form = self.members_share_form

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
            (lbl_members_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15),
            (self.members_share_form, 1, wx.EXPAND | wx.ALL, 15),
            (share_options_sizer, 0, wx.EXPAND | wx.ALL, 15),
            (buttons_sizer, 0, wx.EXPAND | wx.ALL, 15)])
        creation_share_tab.SetSizer(main_sizer)

        self.register_many_i18n('SetLabel', {
            btn_create: N_('Create'),
            btn_cancel: N_('Cancel'),
            rbtn_team_share: N_("Team share"),
            rbtn_public_share: N_("Public share"),
            chk_encryption: N_("Encrypt this share"),
            chk_exclusion: N_('Do not synchronize on this PC'),
            btn_browse_location: N_('Location on this PC'),
            lbl_members: N_('Members accessing this share')
        })

        self.register_many_i18n('SetHint', {
            txt_share_name: N_('Share name')
        })

        self.register_many_i18n('SetToolTipString', {
            btn_back: N_('<< Back to share list'),
        })


def main():
    app = wx.App()
    win = wx.Frame(None, title=N_('New share'))
    app.SetTopWindow(win)
    from os.path import expanduser

    class FakeUserProfile(object):
        def __init__(self):
            self.root_folder_path = expanduser("~")

    class FakeUser(object):
        def __init__(self):
            self.name = "toto"

    app.user_profile = FakeUserProfile()
    app._user = FakeUser()

    tab = CreationShareTab(win)
    tab.GetSizer().SetSizeHints(win)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
