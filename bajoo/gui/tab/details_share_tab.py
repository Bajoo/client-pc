# -*- coding: utf-8 -*-

import logging

import wx
from wx.lib.filebrowsebutton import DirBrowseButton

from ...common.i18n import N_
from ...common.util import human_readable_bytes
from ..base_view import BaseView
from ..event_future import ensure_gui_thread
from ..form.members_share_form import MembersShareForm

_logger = logging.getLogger(__name__)


class DetailsShareTab(wx.Panel):
    """
    The share details tab in the main window, which display
    name, type & status of a share.

    User can also manage this share's all permissions here.
    """

    @ensure_gui_thread
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._share = None
        self._view = DetailsShareView(self)

    @ensure_gui_thread
    def set_data(self, share):
        self._share = share

        self.FindWindow('lbl_share_name').SetLabel(share.name)
        self.FindWindow('lbl_share_nb_members').SetLabel(
            N_('%d members') % len(share.members))
        self.FindWindow('lbl_share_encryption').SetLabel(
            N_('encrypted'))
        self.FindWindow('lbl_share_type').SetLabel(
            N_('Team share'))
        self.FindWindow('lbl_share_status').SetLabel(
            N_('Status:') + ' ' + share.status)
        self.FindWindow('lbl_share_files_folders').SetLabel(
            N_('This share contains %d folders and %d files,') %
            (share.stats['folders'], share.stats['files']))
        self.FindWindow('lbl_local_space').SetLabel(
            N_('which take the disk space of %s') %
            human_readable_bytes(share.stats['space']))
        self.FindWindow('members_share_form') \
            .load_members(share.members)

        self.Layout()


class DetailsShareView(BaseView):
    """View of the details share screen"""

    def __init__(self, details_share_tab):
        BaseView.__init__(self, details_share_tab)

        btn_back = wx.Button(
            details_share_tab, label=N_('<< Back to share list'),
            name='btn_back')
        btn_quit_share = wx.Button(
            details_share_tab, label=N_('Quit this share'),
            name='btn_quit_share')
        btn_delete_share = wx.Button(
            details_share_tab, label=N_('Delete this share'),
            name='btn_delete_share')

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
            details_share_tab,
            label=N_('Open folder'), name='btn_open_folder')

        # the members share form
        lbl_members = wx.StaticText(
            details_share_tab,
            label=N_('Members having access to this share'))
        members_share_form = MembersShareForm(
            details_share_tab, name='members_share_form')

        chk_exclusion = wx.CheckBox(
            details_share_tab, label=N_('Do not synchronize on this PC'),
            name='chk_exclusion')
        btn_browse_location = DirBrowseButton(
            details_share_tab, labelText=N_('Location on this PC'))

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
