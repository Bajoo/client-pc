# -*- coding: utf-8 -*-

import logging

import wx
from wx.lib.filebrowsebutton import DirBrowseButton
from wx.lib.newevent import NewCommandEvent

from ...api.team_share import permission as share_permission
from ...api import MyBajoo, TeamShare
from ...common.i18n import N_
from ..base_view import BaseView
from ..event_future import ensure_gui_thread
from ..form.members_share_form import MembersShareForm
from ..common import message_box

_logger = logging.getLogger(__name__)


class DetailsShareTab(wx.Panel):
    """
    The share details tab in the main window, which display
    name, type & status of a share.

    User can also manage this share's all permissions here.
    """

    RequestShowListShares, EVT_SHOW_LIST_SHARE_REQUEST = NewCommandEvent()
    RequestQuitShare, EVT_QUIT_SHARE_REQUEST = NewCommandEvent()
    RequestDeleteShare, EVT_DELETE_SHARE_REQUEST = NewCommandEvent()

    @ensure_gui_thread
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._share = None
        self._view = DetailsShareView(self)

        self.Bind(MembersShareForm.EVT_SUBMIT, self._on_add_member)
        self.Bind(wx.EVT_BUTTON, self._btn_back_clicked,
                  self.FindWindow('btn_back'))
        self.Bind(wx.EVT_BUTTON, self._btn_open_folder_clicked,
                  self.FindWindow('btn_open_folder'))
        self.Bind(wx.EVT_BUTTON, self._btn_quit_share_clicked,
                  self.FindWindow('btn_quit_share'))
        self.Bind(wx.EVT_BUTTON, self._btn_delete_share_clicked,
                  self.FindWindow('btn_delete_share'))

    @ensure_gui_thread
    def set_data(self, share):
        self._share = share

        self.FindWindow('lbl_share_name').SetLabel(share.name)
        has_member_data = share.container \
                          and type(share.container) is TeamShare \
                          and share.container.members is not None

        if has_member_data:
            self.FindWindow('members_share_form') \
                .load_members(share.container.members)
        else:
            self.FindWindow('members_share_form').Disable()

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
            self.FindWindow('lbl_share_files_folders').SetLabel)
        self._view.remove_i18n(
            self.FindWindow('lbl_local_space').SetLabel)

        self._view.register_many_i18n('SetLabel', {
            self.FindWindow('lbl_share_nb_members'): (
                N_('%d members'),
                len(share.container.members) if has_member_data else 0),
            self.FindWindow('lbl_share_encryption'): N_('encrypted'),
            self.FindWindow('lbl_share_type'): N_('Team share'),
            self.FindWindow('lbl_share_status'): (
                N_('Status: %s'), share.get_status_text()),
            # TODO: stats
            self.FindWindow('lbl_share_files_folders'): N_(' '),
            self.FindWindow('lbl_local_space'): N_(' ')
            # self.FindWindow('lbl_share_files_folders'): (
            # N_('This share contains %d folders and %d files,'),
            # (share.stats['folders'], share.stats['files'])
            # ),
            # self.FindWindow('lbl_local_space'): (
            # N_('which takes the disk space of %s'),
            # human_readable_bytes(share.stats['space'])
            # )
        })

        # If this is the only user, he cannot quit it, but delete it
        if not has_member_data or len(share.container.members) <= 1:
            self.FindWindow('btn_quit_share').Disable()

        # Cannot show members of/delete/quit MyBajoo folder
        show_share_options = True

        if share.container is None or type(share.container) is MyBajoo:
            show_share_options = False

        self.FindWindow('lbl_members').Show(show_share_options)
        self.FindWindow('members_share_form').Show(show_share_options)
        self.FindWindow('btn_quit_share').Enable(show_share_options)
        self.FindWindow('btn_delete_share').Enable(show_share_options)

        self.FindWindow('btn_open_folder').Enable(share.path is not None)
        self.Layout()

    def get_displayed_share(self):
        return self._share

    def add_member_view(self, email, permission):
        member_view_data = dict(permission)
        member_view_data[u'user'] = email

        self._view.members_share_form.on_add_member(member_view_data)

    def _btn_back_clicked(self, _event):
        back_event = DetailsShareTab.RequestShowListShares(self.GetId())
        wx.PostEvent(self, back_event)

    def _on_add_member(self, event):
        # Add permission dict & share object to the event, then forward it
        permission_name = event.permission
        event.permission = dict(share_permission[permission_name])
        event.share = self._share

        event.Skip()

    def _btn_open_folder_clicked(self, _event):
        if self._share and self._share.path:
            from ...common.util import open_folder

            open_folder(self._share.path)
            _logger.debug("Open directory %s", self._share.path)
        else:
            _logger.debug("Unknown container or directory to open")

    def _btn_quit_share_clicked(self, _event):
        if self._share:
            if message_box.message_quit_share(self._share.name, self) \
                    == wx.YES:
                event = DetailsShareTab.RequestQuitShare(self.GetId())
                event.share = self._share
                wx.PostEvent(self, event)

    def _btn_delete_share_clicked(self, _event):
        if self._share:
            if message_box.message_delete_share(self._share.name, self) \
                    == wx.YES:
                event = DetailsShareTab.RequestDeleteShare(self.GetId())
                event.share = self._share
                wx.PostEvent(self, event)


class DetailsShareView(BaseView):
    """View of the details share screen"""

    def __init__(self, details_share_tab):
        BaseView.__init__(self, details_share_tab)

        btn_back = wx.Button(
            details_share_tab, name='btn_back')
        btn_quit_share = wx.Button(
            details_share_tab, name='btn_quit_share')
        btn_delete_share = wx.Button(
            details_share_tab, name='btn_delete_share')

        lbl_share_name = wx.StaticText(
            details_share_tab,
            label='<share_name>', name='lbl_share_name')
        lbl_share_nb_members = wx.StaticText(
            details_share_tab,
            label='# <nb_share_members>', name='lbl_share_nb_members')
        lbl_share_encryption = wx.StaticText(
            details_share_tab,
            label='<is_encrypted>', name='lbl_share_encryption')

        lbl_share_type = wx.StaticText(
            details_share_tab,
            label='<share_type>', name='lbl_share_type')
        lbl_share_status = wx.StaticText(
            details_share_tab,
            label='<share_status>', name='lbl_share_status')
        lbl_share_files_folders = wx.StaticText(
            details_share_tab,
            label='<nb files & folders>', name='lbl_share_files_folders')
        lbl_local_space = wx.StaticText(
            details_share_tab,
            label='<storage_space_taken>', name='lbl_local_space')
        btn_open_folder = wx.Button(
            details_share_tab, name='btn_open_folder')

        # the members share form
        lbl_members = wx.StaticText(details_share_tab, name='lbl_members')
        members_share_form = MembersShareForm(
            details_share_tab, name='members_share_form')
        self.members_share_form = members_share_form

        chk_exclusion = wx.CheckBox(details_share_tab, name='chk_exclusion')
        btn_browse_location = DirBrowseButton(details_share_tab)

        # the top sizer contains the back button
        top_sizer = self.make_sizer(
            wx.HORIZONTAL, [btn_back], outside_border=False)
        buttons_sizer = self.make_sizer(
            wx.HORIZONTAL, [None, btn_quit_share, btn_delete_share],
            outside_border=False)

        # the share description box contains share's name,
        # number of members & whether it is encrypted
        share_description_box = self.make_sizer(
            wx.HORIZONTAL,
            [lbl_share_name, lbl_share_nb_members, lbl_share_encryption],
            outside_border=False)

        # the share summary box contains share type, status,
        # number of files & folders & storage space taken
        share_summary_box = wx.BoxSizer(wx.VERTICAL)
        share_summary_box.AddMany(
            [lbl_share_type, lbl_share_status,
             lbl_share_files_folders, lbl_local_space])

        # the share details box contains the summary
        # and the button to open folder
        share_details_box = self.make_sizer(
            wx.HORIZONTAL, [share_summary_box, None, btn_open_folder])

        # the share_options sizer contains options of exclusion & local dir
        share_options_sizer = self.make_sizer(
            wx.VERTICAL, [chk_exclusion, btn_browse_location],
            flag=wx.EXPAND, outside_border=False)

        # the main sizer
        main_sizer = self.make_sizer(wx.VERTICAL, [top_sizer])
        main_sizer.AddMany([
            (share_description_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15),
            (share_details_box, 0, wx.EXPAND | wx.LEFT, 15),
            (lbl_members, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 15),
            (members_share_form, 1, wx.EXPAND | wx.ALL, 15),
            (share_options_sizer, 0, wx.EXPAND | wx.ALL, 15),
            (buttons_sizer, 0, wx.EXPAND | wx.ALL, 15)
        ])
        details_share_tab.SetSizer(main_sizer)

        self.register_many_i18n('SetLabel', {
            btn_back: N_('<< Back to share list'),
            btn_quit_share: N_('Quit this share'),
            btn_delete_share: N_('Delete this share'),
            btn_open_folder: N_('Open folder'),
            lbl_members: N_('Members having access to this share'),
            chk_exclusion: N_('Do not synchronize on this PC'),
            btn_browse_location: N_('Location on this PC')
        })

        # TODO: disable for next release
        chk_exclusion.Disable()
        btn_browse_location.Disable()


def main():
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
