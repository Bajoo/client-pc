# -*- coding: utf-8 -*-

import logging
from os import path

import wx
from wx.lib.newevent import NewCommandEvent

from ...api import TeamShare, MyBajoo
from ...local_container import LocalContainer
from ...common.i18n import N_
from ..common.pictos import get_bitmap
from ..event_future import ensure_gui_thread
from ..base_view import BaseView
from ..translator import Translator


_logger = logging.getLogger(__name__)


class ListSharesTab(wx.Panel, Translator):
    """
    List shares tab in the main window, which displays
    the status of user's all shares.

    User can then go to the share creation screen or share details screen,
    or can delete a share folder.
    """

    DataRequestEvent, EVT_DATA_REQUEST = NewCommandEvent()
    """
    Send this event to demand for fetching the container list.
    """

    NewShareEvent, EVT_NEW_SHARE = NewCommandEvent()
    """
    Send this event to demand for showing the creation share screen.
    """

    ContainerDetailRequestEvent, EVT_CONTAINER_DETAIL_REQUEST = \
        NewCommandEvent()
    """
    Send this event to demand for fetching container details.

    Attrs:
        container: <bajoo.LocalContainer>
    """

    @ensure_gui_thread
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        Translator.__init__(self)

        self._init_images()

        self._shares = []
        self._view = ListSharesView(self)

        self.Bind(wx.EVT_BUTTON, self._btn_new_share_clicked,
                  self.FindWindow('btn_create_share'))
        self.Bind(wx.EVT_BUTTON, self._btn_refresh_share_list_clicked,
                  self.FindWindow('btn_refresh_share_list'))

    def _init_images(self):
        self.IMG_TEAM_SHARE = get_bitmap(
            'icon_storage_share.png', True, 64, 64)
        self.IMG_MY_BAJOO = get_bitmap(
            'icon_storage_my_bajoo.png', True, 64, 64)
        self.IMG_CONTAINER_DETAILS = get_bitmap(
            'edit-share.png', True, 32, 32)
        self.IMG_QUIT_SHARE = get_bitmap(
            'quit-share.png', True, 32, 32)
        self.IMG_DELETE_SHARE = get_bitmap(
            'delete-share.png', True, 32, 32)
        self.IMG_ENCRYPTED = get_bitmap('lock.png')
        self.IMG_NOT_ENCRYPTED = get_bitmap('unlock.png')
        self.IMG_MEMBERS = get_bitmap('group.png')
        self.IMG_REFRESH = get_bitmap('refresh.png', False)

        self.IMG_CONTAINER_STATUS = {
            LocalContainer.STATUS_ERROR:
                get_bitmap('container_status/error.png'),
            LocalContainer.STATUS_PAUSED:
                get_bitmap('container_status/paused.png'),
            LocalContainer.STATUS_STARTED:
                get_bitmap('container_status/synced.png'),
            LocalContainer.STATUS_STOPPED:
                get_bitmap('container_status/stopped.png'),
            LocalContainer.STATUS_UNKNOWN:
                get_bitmap('container_status/error.png')
        }

    @ensure_gui_thread
    def set_data(self, data):
        self._shares = data.get('shares', [])
        self._view.generate_share_views(self._shares)
        self.show_message(
            data.get('success_msg', None),
            data.get('error_msg', None))
        self._view.end_wait()
        self.Layout()

    def find_share_by_id(self, id):
        """
        """
        if self._shares:
            for share in self._shares:
                if share.id == id:
                    return share

        return None

    def get_container_from_button(self, event, button_prefix):
        """
        Find the container associated to the UI element
        which fired the event.

        Args:
            event (wx.Event): event fired
            button_prefix (str): the prefix string assigned to the button name

        Returns:
            The container object if found, otherwise None.
        """
        name = event.GetEventObject().GetName()
        share_id = name[len(button_prefix):]

        return self.find_share_by_id(share_id)

    def _btn_new_share_clicked(self, event):
        wx.PostEvent(self, self.NewShareEvent(self.GetId()))

    def _btn_refresh_share_list_clicked(self, event):
        self.send_data_request()

    def btn_share_details_clicked(self, event):
        container = self.get_container_from_button(
            event, 'btn_share_details_')

        if container:
            new_event = self.ContainerDetailRequestEvent(self.GetId())
            new_event.container = container
            wx.PostEvent(self, new_event)

    def btn_open_dir_clicked(self, event):
        container = self.get_container_from_button(
            event, 'btn_open_local_dir_')

        if container and container.path:
            from ...common.util import open_folder

            open_folder(container.path)
            _logger.debug("Open directory %s", container.path)
        else:
            _logger.debug("Unknown container or directory to open")

    def send_data_request(self):
        self.set_data({
            'shares': [],
            'success_msg': None,
            'error_msg': None
        })
        wx.PostEvent(self, self.DataRequestEvent(self.GetId()))
        self._view.begin_wait()
        self.Layout()

    def Show(self, show=True):
        # self._send_data_request()
        pass

    def show_message(self, msg=None, error_msg=None):
        lbl_message = self.FindWindow('lbl_message')
        lbl_error_message = self.FindWindow('lbl_error_message')

        if msg:
            self.register_i18n(lbl_message.SetLabel, msg)
            lbl_message.Show()
        else:
            lbl_message.Hide()

        if error_msg:
            self.register_i18n(lbl_error_message.SetLabel, error_msg)
            lbl_error_message.Show()
        else:
            lbl_error_message.Hide()

        self.Layout()

    def hide_messages(self):
        self.FindWindow('lbl_message').Hide()
        self.FindWindow('lbl_error_message').Hide()
        self.Layout()

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self._view.notify_lang_change()


class ListSharesView(BaseView):
    """View of the list shares screen"""

    def __init__(self, list_shares_tab):
        BaseView.__init__(self, list_shares_tab)
        self._share_views = []

        btn_create_share = wx.Button(list_shares_tab,
                                     name='btn_create_share')
        btn_refresh_share_list = wx.BitmapButton(
            list_shares_tab, name='btn_refresh_share_list',
            bitmap=self.window.IMG_REFRESH)
        self._wait = wx.Gauge(self.window)
        self._wait.Hide()
        self._waiting_timer = wx.Timer(self.window)
        self.window.Bind(wx.EVT_TIMER, self._waiting_timer_handler,
                         self._waiting_timer)

        top_box = self.make_sizer(wx.HORIZONTAL, [
            btn_create_share, None, btn_refresh_share_list
        ], outside_border=False)

        lbl_message = wx.StaticText(
            self.window, name='lbl_message')
        lbl_message.SetForegroundColour(wx.BLUE)
        lbl_message.Hide()

        lbl_error_message = wx.StaticText(
            self.window, name='lbl_error_message')
        lbl_error_message.SetForegroundColour(wx.RED)
        lbl_error_message.Hide()

        self.shares_window = wx.ScrolledWindow(self.window)
        self.shares_window.SetScrollbars(1, 1, 1, 1)
        self.shares_window.SetScrollRate(5, 20)

        # The sizer which will contain all the share items
        self.share_sizer = self.make_sizer(wx.VERTICAL, [], False)
        self.shares_window.SetSizer(self.share_sizer)

        main_sizer = self.make_sizer(
            wx.VERTICAL, [top_box, lbl_message, lbl_error_message])
        main_sizer.Add(self.shares_window, 1, wx.EXPAND | wx.ALL, 15)
        main_sizer.Add(self._wait, 0, wx.EXPAND | wx.ALL, 0)
        self.window.SetSizer(main_sizer)
        self.register_i18n(btn_create_share.SetLabel,
                           N_("New share"))
        self.register_i18n(btn_refresh_share_list.SetToolTipString,
                           N_("Refresh"))

    def generate_share_views(self, shares):
        """
        Reload share items in data to the view.
        """
        self._remove_all_share_views()

        for share in shares:
            self._add_share_view(share)

        self.window.GetSizer().Layout()

    def _remove_all_share_views(self):
        for (share_view, share_view_sizer) in self._share_views:
            # Delete the view: it's necessary to do both, and consecutively:
            # remove the child out of its parent
            # then destroy itself.
            self.shares_window.RemoveChild(share_view)
            share_view.Destroy()

            # After all: removing the share_view_sizer
            self.share_sizer.Remove(share_view_sizer)

        self._share_views = []

    def _add_share_view(self, container):
        """
        Add a single box for a share item.
        The name of each control element in this box is suffixed
        with the share id (e.g. lbl_something_<share_id>) so that
        we can populate them correctly later.

        Args:
            container: <LocalContainer>
        """
        share_box = wx.StaticBox(self.shares_window,
                                 name='share_box_' + container.id)

        # By default, set it as a team share icon
        # to prevent unknown container type or, particularly, None.
        img_share = self.window.IMG_TEAM_SHARE

        lbl_share_name = wx.StaticText(
            share_box, label=container.name,
            name='lbl_share_name_' + container.id)
        lbl_share_status_desc = wx.StaticText(share_box)
        img_share_status = wx.StaticBitmap(
            share_box, name='img_share_status_' + container.id)
        lbl_share_status = wx.StaticText(
            share_box, name='lbl_share_status_' + container.id)

        lbl_error_msg = wx.StaticText(
            share_box, name='lbl_error_msg_' + container.id)
        lbl_error_msg.SetForegroundColour(wx.RED)
        lbl_error_msg.SetLabel(container.error_msg or '')

        share_status_box = self.make_sizer(
            wx.HORIZONTAL, [
                lbl_share_status_desc, img_share_status,
                lbl_share_status, lbl_error_msg
            ], outside_border=False)
        img_share_encryption = wx.StaticBitmap(
            share_box, name='img_share_encryption_' + container.id)
        lbl_share_description = wx.StaticText(
            share_box, name='lbl_share_desc_' + container.id)
        img_share_members = wx.StaticBitmap(
            share_box, name='img_share_members_' + container.id,
            bitmap=self.window.IMG_MEMBERS)
        lbl_share_members = wx.StaticText(
            share_box, name='lbl_share_members_' + container.id)

        btn_share_details = wx.BitmapButton(
            share_box, name='btn_share_details_' + container.id,
            bitmap=self.window.IMG_CONTAINER_DETAILS)
        btn_quit_share = wx.BitmapButton(
            share_box, name='btn_share_details_' + container.id,
            bitmap=self.window.IMG_QUIT_SHARE)
        btn_quit_share.Hide()
        btn_delete_share = wx.BitmapButton(
            share_box, name='btn_share_details_' + container.id,
            bitmap=self.window.IMG_DELETE_SHARE)
        btn_delete_share.Hide()
        self.window.Bind(wx.EVT_BUTTON, self.window.btn_share_details_clicked,
                         btn_share_details)

        action_box = self.make_sizer(
            wx.HORIZONTAL, [
                btn_quit_share, btn_delete_share, btn_share_details
            ], outside_border=False)

        if container.container and type(container.container) is MyBajoo:
            img_share = self.window.IMG_MY_BAJOO

        btn_open_local_dir = wx.BitmapButton(
            share_box, bitmap=img_share,
            name='btn_open_local_dir_' + container.id)
        btn_open_local_dir.Enable(
            container.path is not None and
            path.exists(container.path))
        self.window.Bind(wx.EVT_BUTTON, self.window.btn_open_dir_clicked,
                         btn_open_local_dir)

        encrypted_text = 'not encrypted'

        if container.container.is_encrypted:
            encrypted_text = 'encrypted'

        self.register_i18n(
            lbl_share_description.SetLabel,
            N_(encrypted_text))
        img_share_encryption.SetBitmap(
            self.window.IMG_ENCRYPTED if container.container.is_encrypted
            else self.window.IMG_NOT_ENCRYPTED)

        lbl_share_members.Hide()
        img_share_members.Hide()

        # self.register_i18n(lbl_share_description.SetLabel,
        # N_('%d members'), 18)

        share_box_sizer = wx.StaticBoxSizer(share_box)

        description_box = self.make_sizer(
            wx.HORIZONTAL, [
                lbl_share_name, img_share_encryption,
                lbl_share_description, img_share_members, lbl_share_members
            ], False)
        description_status_box = self.make_sizer(
            wx.VERTICAL, [description_box, share_status_box], False)

        share_box_sizer_inside = self.make_sizer(wx.HORIZONTAL, [
            btn_open_local_dir,
            description_status_box, None,
            action_box])
        share_box_sizer.Add(share_box_sizer_inside, 1, wx.EXPAND)

        self.share_sizer.Add(share_box_sizer, 0, wx.EXPAND)
        self._share_views.append((share_box, share_box_sizer))
        self.register_many_i18n('SetLabel', {
            lbl_share_status_desc: N_('Status:'),
            lbl_share_status: N_(container.get_status_text()),
            btn_share_details: N_('Details')
        })

        self.register_many_i18n('SetToolTipString', {
            btn_open_local_dir: N_('Open folder'),
            btn_share_details: N_('Details'),
            btn_quit_share: N_('Quit this share'),
            btn_delete_share: N_('Delete this share')
        })

        img_share_status.SetBitmap(
            self.window.IMG_CONTAINER_STATUS[container.status])

        if container.container and type(container.container) is TeamShare:
            share = container.container

            if hasattr(share, 'members') and share.members:
                n_members = len(share.members)

                self.register_i18n(
                    lbl_share_members.SetLabel,
                    '%d members', n_members)
                lbl_share_members.Show()
                img_share_members.Show()

                is_admin = False
                has_other_admins = False

                for member in share.members:
                    member_email = member.get(u'user')
                    member_admin = member.get(u'admin')

                    if member_admin:
                        if member_email == wx.GetApp().user_profile.email:
                            is_admin = True
                        else:
                            has_other_admins = True

                is_only_admin = is_admin and not has_other_admins

                btn_delete_share.Show(is_admin)
                btn_quit_share.Show(not is_only_admin)
                share_box_sizer.Layout()

    def _waiting_timer_handler(self, _event):
        self._wait.Pulse()

    def begin_wait(self):
        self._waiting_timer.Start(100)
        self._wait.Show()

    def end_wait(self):
        self._waiting_timer.Stop()
        self._wait.Hide()


def main():
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    app = wx.App()
    win = wx.Frame(None, title=N_('My Shares'))
    app.SetTopWindow(win)

    tab = ListSharesTab(win)
    tab.GetSizer().SetSizeHints(win)

    from ...api import Session, Container

    def _on_fetch_session(session):
        return Container.list(session)

    def _on_fetch_shares(shares):
        tab.set_data({
            'shares': shares,
            'success_msg': None,
            'error_msg': None
        })

    def _on_request_data(event):
        Session.create_session(
            'stran+20@bajoo.fr',
            'stran+20@bajoo.fr') \
            .then(_on_fetch_session) \
            .then(_on_fetch_shares)

    app.Bind(ListSharesTab.EVT_DATA_REQUEST, _on_request_data)

    tab.Show()
    win.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
