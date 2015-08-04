# -*- coding: utf-8 -*-

import logging

import wx
from wx.lib.newevent import NewCommandEvent

from ...api import MyBajoo, TeamShare
from ...common.i18n import N_
from ..event_future import ensure_gui_thread
from ..base_view import BaseView


_logger = logging.getLogger(__name__)


class ListSharesTab(wx.Panel):
    """
    List shares tab in the main window, which displays
    the status of user's all shares.

    User can then go to the share creation screen or share details screen,
    or can delete a share folder.
    """

    DataRequestEvent, EVT_DATA_REQUEST = NewCommandEvent()
    NewShareEvent, EVT_NEW_SHARE = NewCommandEvent()
    ShareDetailRequestEvent, EVT_SHARE_DETAIL_REQUEST = NewCommandEvent()

    TEAM_SHARE_ICON = None
    MY_BAJOO_ICON = None
    FOLDER_ICON = None

    @ensure_gui_thread
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._init_images()

        self._shares = []
        self._view = ListSharesView(self)

        self.Bind(wx.EVT_BUTTON, self._btn_new_share_clicked,
                  self.FindWindow('btn_create_share'))

    def _init_images(self):
        if not ListSharesTab.TEAM_SHARE_ICON:
            ListSharesTab.TEAM_SHARE_ICON = wx.Image(
                'bajoo/assets/images/favicon-partage.png') \
                .Scale(64, 64, wx.IMAGE_QUALITY_HIGH) \
                .ConvertToBitmap()

        if not ListSharesTab.MY_BAJOO_ICON:
            ListSharesTab.MY_BAJOO_ICON = wx.Image(
                'bajoo/assets/images/picto-mon-bajoo.png') \
                .Scale(64, 64, wx.IMAGE_QUALITY_HIGH) \
                .ConvertToBitmap()

        if not ListSharesTab.FOLDER_ICON:
            ListSharesTab.FOLDER_ICON = wx.Image(
                'bajoo/assets/images/folder.png') \
                .ConvertToBitmap()

    @ensure_gui_thread
    def set_data(self, shares):
        self._shares = shares
        self._view.generate_share_views(shares)
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

    def btn_share_details_clicked(self, event):
        share = self.get_container_from_button(event, 'btn_share_details_')

        if share:
            new_event = self.ShareDetailRequestEvent(self.GetId())
            new_event.share = share
            wx.PostEvent(self, new_event)

    def Show(self, show=True):
        wx.PostEvent(self, self.DataRequestEvent(self.GetId()))


class ListSharesView(BaseView):
    """View of the list shares screen"""

    def __init__(self, list_shares_tab):
        BaseView.__init__(self, list_shares_tab)
        self._share_views = []

        btn_create_share = wx.Button(list_shares_tab, name='btn_create_share')

        self.shares_window = wx.ScrolledWindow(self.window)
        self.shares_window.SetScrollbars(1, 1, 1, 1)
        self.shares_window.SetScrollRate(5, 20)

        # The sizer which will contain all the share items
        self.share_sizer = self.make_sizer(wx.VERTICAL, [], False)
        self.shares_window.SetSizer(self.share_sizer)

        main_sizer = self.make_sizer(
            wx.VERTICAL, [btn_create_share])
        main_sizer.Add(self.shares_window, 1, wx.EXPAND | wx.ALL, 15)
        self.window.SetSizer(main_sizer)
        self.register_i18n(btn_create_share.SetLabel, N_("New share"))

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

    def _add_share_view(self, share):
        """
        Add a single box for a share item.
        The name of each control element in this box is suffixed
        with the share id (e.g. lbl_something_<share_id>) so that
        we can populate them correctly later.
        """
        share_box = wx.StaticBox(self.shares_window,
                                 name='share_box_' + share.id)

        img_share = None
        lbl_share_name = wx.StaticText(
            share_box, label=share.name,
            name='lbl_share_name_' + share.id)
        lbl_share_status_desc = wx.StaticText(share_box)
        lbl_share_status = wx.StaticText(
            share_box, name='lbl_share_status_' + share.id)
        share_status_box = self.make_sizer(wx.HORIZONTAL, [
            lbl_share_status_desc, lbl_share_status], outside_border=False)
        lbl_share_description = wx.StaticText(
            share_box, name='lbl_share_desc_' + share.id)

        btn_share_details = wx.Button(
            share_box, name='btn_share_details_' + share.id)
        self.window.Bind(wx.EVT_BUTTON, self.window.btn_share_details_clicked,
                         btn_share_details)

        btn_open_local_dir = wx.BitmapButton(
            share_box, bitmap=ListSharesTab.FOLDER_ICON,
            name='btn_open_local_dir_' + share.id)

        if type(share) is MyBajoo:
            img_share = ListSharesTab.MY_BAJOO_ICON
            self.register_i18n(lbl_share_description.SetLabel,
                               N_('encrypted'))
        elif type(share) is TeamShare:
            img_share = ListSharesTab.TEAM_SHARE_ICON
            # TODO: get number of members
            self.register_i18n(lbl_share_description.SetLabel,
                               N_('%d members'), 18)

        share_box_sizer = wx.StaticBoxSizer(share_box)

        description_box = self.make_sizer(
            wx.HORIZONTAL, [lbl_share_name, lbl_share_description], False)
        description_status_box = self.make_sizer(
            wx.VERTICAL, [description_box, share_status_box], False)

        share_box_sizer_inside = self.make_sizer(wx.HORIZONTAL, [
            wx.StaticBitmap(share_box, label=img_share),
            description_status_box, None,
            btn_share_details, btn_open_local_dir])
        share_box_sizer.Add(share_box_sizer_inside, 1, wx.EXPAND)

        self.share_sizer.Add(share_box_sizer, 0, wx.EXPAND)
        self._share_views.append((share_box, share_box_sizer))
        self.register_many_i18n('SetLabel', {
            lbl_share_status_desc: N_('Status: '),
            # TODO: share status
            lbl_share_status: N_('<status>'),
            btn_share_details: N_('Details')
        })


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
        tab.set_data(shares)

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
