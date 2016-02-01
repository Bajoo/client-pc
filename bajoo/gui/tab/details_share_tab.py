# -*- coding: utf-8 -*-

import logging
from os import path

import wx
from wx.lib.newevent import NewCommandEvent

from ...api.team_share import permission as share_permission
from ...api import TeamShare
from ...local_container import LocalContainer
from ...common.i18n import N_, _
from ..base_view import BaseView
from ..event_promise import ensure_gui_thread
from ..form.members_share_form import MembersShareForm
from ..form.base_form import BaseForm
from ..common import message_box
from ..common.share_location_browser import ShareLocationBrowser
from ..common.pictos import get_bitmap
from ...common.util import human_readable_bytes


_logger = logging.getLogger(__name__)


class DetailsShareTab(BaseForm):
    """
    The share details tab in the main window, which display
    name, type & status of a share.

    User can also manage this share's all permissions here.
    """

    RequestShowListShares, EVT_SHOW_LIST_SHARE_REQUEST = NewCommandEvent()
    RequestQuitShare, EVT_QUIT_SHARE_REQUEST = NewCommandEvent()
    RequestDeleteShare, EVT_DELETE_SHARE_REQUEST = NewCommandEvent()
    RequestStopSyncContainer, EVT_STOP_SYNC_CONTAINER_REQUEST \
        = NewCommandEvent()
    RequestStartSyncContainer, EVT_START_SYNC_CONTAINER_REQUEST \
        = NewCommandEvent()
    RequestMoveContainer, EVT_MOVE_CONTAINER_REQUEST \
        = NewCommandEvent()

    def __init__(self, parent):
        BaseForm.__init__(self, parent)
        self._init_images()
        self._share = None
        self._user_email = None
        self._view = DetailsShareView(self)

        self.Bind(MembersShareForm.EVT_SUBMIT, self._on_add_member)
        self.Bind(MembersShareForm.EVT_REMOVE_MEMBER, self._on_remove_member)
        self.Bind(MembersShareForm.EVT_SELECT_MEMBER, self._on_select_member)
        self.Bind(wx.EVT_BUTTON, self._btn_back_clicked,
                  self.FindWindow('btn_back'))
        self.Bind(wx.EVT_BUTTON, self._btn_open_folder_clicked,
                  self.FindWindow('btn_open_folder'))
        self.Bind(wx.EVT_BUTTON, self._btn_quit_share_clicked,
                  self.FindWindow('btn_quit_share'))
        self.Bind(wx.EVT_BUTTON, self._btn_delete_share_clicked,
                  self.FindWindow('btn_delete_share'))
        self.Bind(wx.EVT_CHECKBOX, self._chk_exclusion_checked,
                  self.FindWindow('chk_exclusion'))
        self.Bind(wx.EVT_TEXT, self._on_location_changed,
                  self.FindWindow('btn_browse_location'))
        self.Bind(wx.EVT_BUTTON, self._on_options_applied, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self._on_options_reset, id=wx.ID_CANCEL)

    def _init_images(self):
        self.IMG_ENCRYPTED = get_bitmap('lock.png')
        self.IMG_NOT_ENCRYPTED = get_bitmap('unlock.png')
        self.IMG_MEMBERS = get_bitmap('group.png', False)
        self.IMG_BACK = get_bitmap('previous.png', False)
        self.IMG_QUIT_SHARE = get_bitmap('quit-share.png', False)
        self.IMG_DELETE_SHARE = get_bitmap('delete-share.png', False)
        self.IMG_OPEN_FOLDER = get_bitmap('open-folder.png', False)

        self.IMG_CONTAINER_STATUS = {
            LocalContainer.STATUS_ERROR:
                get_bitmap('container_status/error.png'),
            LocalContainer.STATUS_PAUSED:
                get_bitmap('container_status/paused.png'),
            LocalContainer.STATUS_STARTED:
                get_bitmap('container_status/synced.png'),
            LocalContainer.STATUS_STOPPED:
                get_bitmap('container_status/stopped.png'),
            LocalContainer.STATUS_QUOTA_EXCEEDED:
                get_bitmap('container_status/error.png'),
            LocalContainer.STATUS_WAIT_PASSPHRASE:
                get_bitmap('container_status/error.png'),
            LocalContainer.STATUS_UNKNOWN:
                get_bitmap('container_status/error.png')
        }

    def _has_member_data(self):
        if not self._share.container:
            return False
        if type(self._share.container) is not TeamShare:
            return False
        return self._share.container.members is not None

    def _check_admin_status(self):
        has_member_data = self._has_member_data()
        is_admin = False
        has_other_admins = False

        if has_member_data:
            for member in self._share.container.members:
                member_email = member.get(u'user')
                member_admin = member.get(u'admin')

                if member_admin:
                    if member_email == self._user_email:
                        is_admin = True
                    else:
                        has_other_admins = True

        is_only_admin = is_admin and not has_other_admins

        return is_admin, is_only_admin

    def _chk_exclusion_checked(self, event):
        do_not_sync = self.FindWindow('chk_exclusion').GetValue()
        btn_browse = self.FindWindow('btn_browse_location')
        btn_browse.Enable(not do_not_sync)

        # Set the default value for the location
        if not do_not_sync:
            if self._share.model.path is None:
                btn_browse.SetValue(path.join(
                    wx.GetApp().user_profile.root_folder_path,
                    _('Shares'), self._share.model.name))
            else:
                btn_browse.SetValue(self._share.model.path)

        self.set_options_buttons_status()

    def _on_location_changed(self, event):
        share_path = self.FindWindow('btn_browse_location').GetValue()
        lbl_folder_exist_error = self.FindWindow('lbl_folder_exist_error')

        if share_path != self._share.model.path and \
                path.exists(share_path):
            self.FindWindow('btn_apply').Enable(False)
            lbl_folder_exist_error.Show()

            return

        lbl_folder_exist_error.Hide()
        self.set_options_buttons_status()
        self.Layout()

    def _on_options_applied(self, event):
        do_not_sync = self.FindWindow('chk_exclusion').GetValue()
        share_path = self.FindWindow('btn_browse_location').GetValue()

        if do_not_sync != self._share.model.do_not_sync:
            # User changes the sync status
            self._share.model.do_not_sync = do_not_sync

            if do_not_sync:
                event = self.RequestStopSyncContainer(self.GetId())
                event.container = self._share
                wx.PostEvent(self, event)
            else:
                # TODO: check valid directory
                self._share.model.path = share_path
                event = self.RequestStartSyncContainer(self.GetId())
                event.container = self._share
                wx.PostEvent(self, event)

            self.disable()

        elif not do_not_sync and share_path != self._share.model.path:
            # Always sync this container, but move its path
            event = self.RequestMoveContainer(self.GetId())
            event.container = self._share
            event.path = share_path
            wx.PostEvent(self, event)

            self.disable()

    def set_options_buttons_status(self):
        """
        Enable Apply/Cancel only if has changed
        """
        has_change = \
            self._share.model.do_not_sync != self.FindWindow(
                'chk_exclusion').GetValue() or \
            (self._share.model.path != self.FindWindow(
                'btn_browse_location').GetValue() and
             not self._share.model.do_not_sync)

        self.FindWindow('btn_apply').Enable(has_change)
        self.FindWindow('btn_cancel').Enable(has_change)

    def _on_options_reset(self, event):
        self.set_share_options_value(self._share)

    def set_share_options_value(self, share):
        do_not_sync = share.model.do_not_sync
        share_path = share.model.path

        self.FindWindow('chk_exclusion').SetValue(do_not_sync)

        if share_path:
            self.FindWindow('btn_browse_location').SetValue(
                share_path or '')

        self.FindWindow('btn_browse_location').Enable(not do_not_sync)

    @ensure_gui_thread
    def set_data(self, share, success_msg=None, error_msg=None):
        """Display data received about the container.

        Args:
            share (LocalContainer)
        """
        self._share = share
        n_folders, n_files, folder_size = share.get_stats()
        friendly_folders_size = human_readable_bytes(folder_size)

        self.FindWindow('lbl_share_name').SetLabel(share.model.name)
        has_member_data = self._has_member_data()
        is_encrypted = share.container and share.container.is_encrypted
        share_type = N_('Team share') \
            if share.container and type(share.container) is TeamShare \
            else N_('Personal folder')

        if has_member_data:
            self.FindWindow('members_share_form') \
                .load_members(share.container.members)
        else:
            self.FindWindow('members_share_form').Disable()

        self.FindWindow('img_share_encryption').SetBitmap(
            self.IMG_ENCRYPTED if is_encrypted else self.IMG_NOT_ENCRYPTED)

        # Remove all i18n registrations
        self._view.remove_i18n(
            self.FindWindow('lbl_share_nb_members').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_share_encryption').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_share_type').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_share_status').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_share_container_status').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_share_files_folders').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_local_space').SetLabel)

        self._view.register_many_i18n('SetLabel', {
            self.FindWindow('lbl_share_nb_members'): (
                N_('%d members'),
                len(share.container.members) if has_member_data else 0
            ),
            self.FindWindow('lbl_share_encryption'): (
                N_('Encrypted') if is_encrypted else N_('Not encrypted')
            ),
            self.FindWindow('lbl_share_type'): share_type,
            self.FindWindow('lbl_share_status'): (N_('Status:')),
            self.FindWindow('lbl_share_container_status'): (
                share.get_status_text()),
            # TODO: stats
            self.FindWindow('lbl_share_files_folders'): ' ',
            self.FindWindow('lbl_local_space'): ' ',
            self.FindWindow('lbl_share_files_folders'): (
                N_('This share contains %(n_folders)d folders ' +
                   'and %(n_files)d files,'),
                {"n_folders": n_folders, "n_files": n_files}
            ),
            self.FindWindow('lbl_local_space'): (
                N_('which takes the disk space of %s'), friendly_folders_size
            )
        })

        self.FindWindow('img_share_status').SetBitmap(
            self.IMG_CONTAINER_STATUS[share.get_status()])

        # Cannot show members of/delete/quit MyBajoo folder
        show_share_options = \
            self._share.container and type(self._share.container) is TeamShare

        self.FindWindow('lbl_share_nb_members').Show(
            show_share_options and has_member_data)
        self.FindWindow('btn_open_folder').Enable(
            share.model.path is not None and
            path.exists(share.model.path))

        if share.error_msg:
            self.show_error_message(share.error_msg)
        else:
            self.hide_message()

        if show_share_options:
            self._user_email = wx.GetApp()._user.name
            self._refresh_admin_controls()

        self.set_share_options_value(self._share)
        self.FindWindow('btn_browse_location').set_share_name(
            share.model.name, set_value_now=False)
        self.set_options_buttons_status()

        lbl_options_success = self.FindWindow('lbl_options_success')
        lbl_options_success.SetLabel(success_msg or '')
        lbl_options_success.Show(success_msg is not None)

        lbl_options_error = self.FindWindow('lbl_options_error')
        lbl_options_error.SetLabel(error_msg or '')
        lbl_options_error.Show(error_msg is not None)

        if share.is_moving:
            self.disable()

        self.Layout()

    @ensure_gui_thread
    def _refresh_admin_controls(self):
        show_share_options = \
            self._share.container and type(self._share.container) is TeamShare
        is_admin, is_only_admin = self._check_admin_status()

        show_admin = show_share_options and is_admin
        show_quit = show_share_options and not is_only_admin

        self.FindWindow('lbl_members').Show(show_admin)
        self.FindWindow('img_members').Show(show_admin)
        self.FindWindow('members_share_form').Show(show_admin)
        self.FindWindow('btn_delete_share').Enable(show_admin)
        self.FindWindow('btn_quit_share').Enable(show_quit)

        self.Refresh()
        self.Layout()

    def Show(self, show=True):
        BaseForm.Show(self, show)

        # Hide administration controls by default
        self.hide_message()
        self.FindWindow('lbl_members').Hide()
        self.FindWindow('img_members').Hide()
        self.FindWindow('members_share_form').Hide()
        self.FindWindow('btn_delete_share').Disable()
        self.FindWindow('btn_quit_share').Enable()

    def get_displayed_share(self):
        return self._share

    def add_member_view(self, email, permission):
        member_view_data = dict(permission)
        member_view_data[u'user'] = email

        self._view.members_share_form.on_add_member(member_view_data)
        self._refresh_admin_controls()

    def remove_member_view(self, email):
        self._view.members_share_form.on_remove_member(email)
        self._refresh_admin_controls()

    def _btn_back_clicked(self, _event):
        self.hide_message()
        back_event = DetailsShareTab.RequestShowListShares(self.GetId())
        wx.PostEvent(self, back_event)

    def _on_add_member(self, event):
        self.hide_message()
        # Add permission dict & share object to the event, then forward it
        permission_name = event.permission
        event.permission = dict(share_permission[permission_name])
        event.share = self._share

        event.Skip()
        self.disable()

    def _on_remove_member(self, event):
        self.hide_message()
        event.share = self._share
        event.Skip()
        self.disable()

    def _on_select_member(self, event):
        email = event.email
        is_admin, is_only_admin = self._check_admin_status()

        if email == self._user_email:
            self.FindWindow('members_share_form').enable_change_rights(
                is_admin and not is_only_admin)
        else:
            self.FindWindow('members_share_form').enable_change_rights(
                is_admin)

    def _btn_open_folder_clicked(self, _event):
        self.hide_message()

        if self._share and self._share.model.path:
            from ...common.util import open_folder

            open_folder(self._share.model.path)
            _logger.debug("Open directory %s", self._share.model.path)
        else:
            _logger.debug("Unknown container or directory to open")

    def _btn_quit_share_clicked(self, _event):
        self.hide_message()

        if self._share:
            if message_box.message_box_quit_share(self._share.model.name,
                                                  self) \
                    == wx.YES:
                event = DetailsShareTab.RequestQuitShare(self.GetId())
                event.share = self._share
                wx.PostEvent(self, event)

                self.disable()

    def _btn_delete_share_clicked(self, _event):
        self.hide_message()

        if self._share:
            if message_box.message_box_delete_share(self._share.model.name,
                                                    self) \
                    == wx.YES:
                event = DetailsShareTab.RequestDeleteShare(self.GetId())
                event.share = self._share
                wx.PostEvent(self, event)

                self.disable()

    def _show_message(self, message, text_color):
        lbl_message = self.FindWindow('lbl_message')
        self.register_i18n(lbl_message.SetLabel, message)
        lbl_message.SetForegroundColour(text_color)
        lbl_message.Show()
        self.Layout()

    def show_message(self, message):
        self._show_message(message, wx.BLUE)

    def show_error_message(self, message):
        self._show_message(message, wx.RED)

    def hide_message(self):
        self.FindWindow('lbl_message').Hide()
        self.Layout()

    def notify_lang_change(self):
        BaseForm.notify_lang_change(self)
        self._view.notify_lang_change()


class DetailsShareView(BaseView):
    """View of the details share screen"""

    def __init__(self, details_share_tab):
        BaseView.__init__(self, details_share_tab)

        btn_back = wx.BitmapButton(
            details_share_tab, name='btn_back',
            bitmap=details_share_tab.IMG_BACK)
        btn_quit_share = wx.Button(
            details_share_tab, name='btn_quit_share',
            label=N_('Quit this share'))
        btn_quit_share.SetBitmap(details_share_tab.IMG_QUIT_SHARE)
        btn_delete_share = wx.Button(
            details_share_tab, name='btn_delete_share',
            label=N_('Delete this share'))
        btn_delete_share.SetBitmap(details_share_tab.IMG_DELETE_SHARE)

        lbl_share_name = wx.StaticText(
            details_share_tab,
            label=_('Loading ...'), name='lbl_share_name')
        lbl_share_nb_members = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_nb_members')
        img_share_encryption = wx.StaticBitmap(
            details_share_tab, name='img_share_encryption')
        lbl_share_encryption = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_encryption')

        lbl_share_type = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_type')
        img_share_status = wx.StaticBitmap(
            details_share_tab, name='img_share_status')
        lbl_share_status = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_status')
        lbl_share_container_status = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_container_status')
        lbl_share_status_box = self.make_sizer(
            wx.HORIZONTAL, [lbl_share_status,
                            lbl_share_container_status,
                            img_share_status],
            outside_border=False, flag=wx.ALIGN_CENTER)
        lbl_share_files_folders = wx.StaticText(
            details_share_tab,
            label='', name='lbl_share_files_folders')
        lbl_local_space = wx.StaticText(
            details_share_tab,
            label='', name='lbl_local_space')
        btn_open_folder = wx.Button(
            details_share_tab, name='btn_open_folder',
            label=N_('Open folder'))
        btn_open_folder.SetBitmap(details_share_tab.IMG_OPEN_FOLDER)

        # the members share form
        img_members = wx.StaticBitmap(
            details_share_tab, label=details_share_tab.IMG_MEMBERS,
            name='img_members')
        lbl_members = wx.StaticText(details_share_tab, name='lbl_members')
        lbl_members_box = self.make_sizer(
            wx.HORIZONTAL, [img_members, lbl_members],
            outside_border=False, flag=wx.ALIGN_CENTER)
        members_share_form = MembersShareForm(
            details_share_tab, name='members_share_form')
        self.members_share_form = members_share_form

        lbl_options_success = wx.StaticText(
            details_share_tab, name='lbl_options_success')
        lbl_options_success.SetForegroundColour(wx.BLUE)
        lbl_options_success.Hide()

        lbl_options_error = wx.StaticText(
            details_share_tab, name='lbl_options_error')
        lbl_options_error.SetForegroundColour(wx.RED)
        lbl_options_error.Hide()

        chk_exclusion = wx.CheckBox(details_share_tab, name='chk_exclusion')
        btn_browse_location = ShareLocationBrowser(
            parent=details_share_tab, name='btn_browse_location')

        btn_cancel = wx.Button(details_share_tab, wx.ID_CANCEL,
                               name='btn_cancel')
        btn_apply = wx.Button(details_share_tab, wx.ID_APPLY,
                              name='btn_apply')

        # the top sizer contains the back button
        top_sizer = self.make_sizer(
            wx.HORIZONTAL, [btn_back], outside_border=False)
        buttons_sizer = self.make_sizer(
            wx.HORIZONTAL, [None, btn_quit_share, btn_delete_share],
            outside_border=False)

        # the share description box contains share's name,
        # number of members & whether it is encrypted
        share_description_box = self.make_sizer(
            wx.HORIZONTAL, [
                lbl_share_name, lbl_share_nb_members,
                img_share_encryption, lbl_share_encryption
            ], outside_border=False, flag=wx.ALIGN_CENTER)

        # the share summary box contains share type, status,
        # number of files & folders & storage space taken
        share_summary_box = wx.BoxSizer(wx.VERTICAL)
        share_summary_box.AddMany(
            [lbl_share_type, lbl_share_status_box,
             lbl_share_files_folders, lbl_local_space])

        # the share details box contains the summary
        # and the button to open folder
        share_details_box = self.make_sizer(
            wx.HORIZONTAL, [share_summary_box, None, btn_open_folder])

        # lbl_member_message
        lbl_message = wx.StaticText(
            details_share_tab, name='lbl_message')
        lbl_message.Hide()

        lbl_folder_exist_error = wx.StaticText(
            details_share_tab, name='lbl_folder_exist_error')
        lbl_folder_exist_error.SetForegroundColour(wx.RED)

        # the button sizer
        share_options_buttons = wx.StdDialogButtonSizer()
        share_options_buttons.SetAffirmativeButton(btn_apply)
        share_options_buttons.SetCancelButton(btn_cancel)
        share_options_buttons.Add(lbl_folder_exist_error)
        share_options_buttons.Realize()

        # the share_options sizer contains options of exclusion & local dir
        share_options_box = wx.StaticBox(
            details_share_tab, label=N_('Advanced options'))
        share_options_box_sizer = wx.StaticBoxSizer(
            share_options_box, wx.VERTICAL)

        share_options_sizer = self.make_sizer(
            wx.VERTICAL, [
                lbl_options_success, lbl_options_error,
                chk_exclusion, btn_browse_location,
                share_options_buttons],
            flag=wx.EXPAND,
            sizer=share_options_box_sizer)

        # the main sizer
        main_sizer = self.make_sizer(wx.VERTICAL, [top_sizer])
        main_sizer.AddMany([
            (share_description_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15),
            (share_details_box, 0, wx.EXPAND | wx.LEFT, 15),
            (lbl_message, 0, wx.EXPAND | wx.ALL, 15),
            (lbl_members_box, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 15),
            (members_share_form, 1, wx.EXPAND | wx.ALL, 15),
            (share_options_sizer, 0, wx.EXPAND | wx.ALL, 15),
            (buttons_sizer, 0, wx.EXPAND | wx.ALL, 15)
        ])
        details_share_tab.SetSizer(main_sizer)

        self.register_many_i18n('SetLabel', {
            lbl_members: N_('Members having access to this share'),
            chk_exclusion: N_('Do not synchronize on this PC'),
            btn_browse_location: N_('Location on this PC'),
            lbl_folder_exist_error: N_('This folder already exists'),
            btn_quit_share: N_('Quit this share'),
            btn_delete_share: N_('Delete this share'),
            btn_open_folder: N_('Open folder'),
            share_options_box: N_('Advanced options'),
            btn_cancel: N_('Cancel'),
            btn_apply: N_('Apply')
        })

        self.register_many_i18n('SetToolTipString', {
            btn_back: N_('<< Back to share list')
        })


def main():
    # FIXME this code seems to be broken.
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    app = wx.App()
    win = wx.Frame(None, title=N_('Share Details'))
    app.SetTopWindow(win)

    tab = DetailsShareTab(win)
    tab.GetSizer().SetSizeHints(win)

    from ...api.session import Session
    from ...api.container import Container

    share = None

    def list_containers(session):
        return Container.list(session)

    def set_current_share(containers):
        global share
        share = containers[-1]
        return share.list_members()

    def set_share_members(members):
        global share
        share.members = members
        return None

    def set_share_local_info(_future_result):
        global share
        _logger.debug(share.name)
        _logger.debug(share.members)

        share.encrypted = True
        share.status = 'Synced'
        share.stats = {
            'folders': 4,
            'files': 168,
            'space': 260000000
        }

    @ensure_gui_thread
    def load_data_to_view(_future_result):
        global share
        win.Show(True)
        tab.set_data(share)

        return None

    Session.create_session('stran+20@bajoo.fr', 'stran+20@bajoo.fr') \
        .then(list_containers) \
        .then(set_current_share) \
        .then(set_share_members) \
        .then(set_share_local_info) \
        .then(load_data_to_view)

    win.Show(False)
    app.MainLoop()


if __name__ == '__main__':
    main()
