# -*- coding: utf-8 -*-

import logging

import wx

from ..common.i18n import N_
from ..common.path import resource_filename
from ..gui.event_future import ensure_gui_thread
from .tab import ListSharesTab
from .tab import CreationShareTab
from .tab import DetailsShareTab
from .tab import AccountTab
from .tab import GeneralSettingsTab
from .tab import NetworkSettingsTab
from .tab import AdvancedSettingsTab
from .translator import Translator

_logger = logging.getLogger(__name__)


class MainWindow(wx.Frame):
    LIST_SHARES_TAB = 0
    ACCOUNT_TAB = 1
    GENERAL_SETTINGS_TAB = 2
    NETWORK_SETTINGS_TAB = 3
    ADVANCED_SETTINGS_TAB = 4

    def __init__(self):
        wx.Frame.__init__(self, parent=None, size=(800, 600))
        self.SetMinSize((800, 600))
        self._view = MainWindowListbook(self)

        icon_path = resource_filename('assets/images/favicon.png')
        icon = wx.Icon(icon_path)
        self.SetIcon(icon)

        sizer = wx.BoxSizer()
        sizer.Add(self._view, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.Bind(ListSharesTab.EVT_NEW_SHARE,
                  self._on_request_create_new_share)
        self.Bind(ListSharesTab.EVT_CONTAINER_DETAIL_REQUEST,
                  self._on_request_share_details)
        self.Bind(CreationShareTab.EVT_SHOW_LIST_SHARE_REQUEST,
                  self._on_request_show_list_shares)
        self.Bind(DetailsShareTab.EVT_SHOW_LIST_SHARE_REQUEST,
                  self._on_request_show_list_shares)

    def notify_lang_change(self):
        self._view.notify_lang_change()

    def _show_tab(self, tab_index):
        # Remove all temperatory tabs
        while self._view.GetPageCount() > 5:
            self._view.DeletePage(5)

        self._view.details_share_tab = None
        self._view.creation_shares_tab = None

        self._view.SetSelection(tab_index)

    def _show_share_tab(self, share_tab):
        """
        We have 3 share-related tabs,
        this function will display the share_tab at first place,
        & hide the 2 other ones.
        """
        if self._view.GetPageCount() > 5:
            self._view.DeletePage(5)
            self._view.InsertPage(5, share_tab, "", select=True)
        else:
            self._view.AddPage(share_tab, "", select=True)

    def on_tab_changed(self, event):
        if hasattr(self, '_view') \
                and self._view.GetSelection() < 5:
            while self._view.GetPageCount() > 5:
                self._view.DeletePage(5)

            self._view.details_share_tab = None
            self._view.creation_shares_tab = None

    @ensure_gui_thread
    def show_account_tab(self):
        """Make the account tab shown on top."""
        self._show_tab(MainWindow.ACCOUNT_TAB)

    @ensure_gui_thread
    def show_list_shares_tab(self):
        """Make the share list tab shown on top."""
        self._show_tab(MainWindow.LIST_SHARES_TAB)

    @ensure_gui_thread
    def show_creation_shares_tab(self):
        """Make the creation share tab shown on top."""
        self._show_share_tab(self._view.creation_shares_tab)

    @ensure_gui_thread
    def show_details_share_tab(self, share):
        self._show_share_tab(self._view.details_share_tab)
        self._view.details_share_tab.set_data(share)

    @ensure_gui_thread
    def show_general_settings_tab(self):
        """Make the general settings tab shown on top."""
        self._show_tab(MainWindow.GENERAL_SETTINGS_TAB)

    @ensure_gui_thread
    def show_advanced_settings_tab(self):
        """Make the advanced settings tab shown on top."""
        self._show_tab(MainWindow.ADVANCED_SETTINGS_TAB)

    @ensure_gui_thread
    def show_network_settings_tab(self):
        """Make the network settings tab shown on top."""
        self._show_tab(MainWindow.NETWORK_SETTINGS_TAB)

    @ensure_gui_thread
    def set_account_info(self, account_info):
        """
        Args:
            account_info (dict)
        """
        if self._view.account_tab:
            for key, value in account_info.items():
                self._view.account_tab.set_data(key, value)

            self._view.account_tab.populate()

    @ensure_gui_thread
    def load_shares(self, shares):
        """
        load & display the shares on share list tab.

        Args:
            shares: list of LocalContainer
        """
        self._view.list_shares_tab.set_data(shares)

    @ensure_gui_thread
    def set_share_details(self, share_details):
        if self._view.details_share_tab:
            self._view.details_share_tab.set_data(share_details)

    @ensure_gui_thread
    def load_config(self, config):
        self._view.general_settings_tab.load_config(config)
        self._view.advanced_settings_tab.load_config(config)
        self._view.network_settings_tab.load_config(config)

    @ensure_gui_thread
    def on_new_share_created(self, new_share):
        # TODO: show notification
        if self._view.creation_shares_tab:
            self._view.creation_shares_tab.enable()

        self.show_list_shares_tab()

    @ensure_gui_thread
    def on_share_member_added(self, share, email, permission):
        if self._view.details_share_tab:
            if self._view.details_share_tab.get_displayed_share() is share:
                self._view.details_share_tab.add_member_view(
                    email, permission)

            self._view.details_share_tab.enable()

    def on_quit_or_delete_share(self, share):
        """
        After quit or delete successfully a share,
        navigate back to share list,
        and reenable the detail share panel.
        Otherwise, reenable & stay at the detail share panel.

        Args:
            share (TeamShare): the deleted or quit share.
                Set it to None if operation failed.
        """
        if self._view.details_share_tab:
            self._view.details_share_tab.enable()

        if share:
            self.show_list_shares_tab()

    def _on_request_show_list_shares(self, _event):
        self.show_list_shares_tab()

    def _on_request_create_new_share(self, _event):
        """When the button new share on the share list tab is clicked,
        show the creation share tab."""
        self._view.creation_shares_tab = CreationShareTab(self._view)
        self.show_creation_shares_tab()

    def _on_request_share_details(self, event):
        self._view.details_share_tab = DetailsShareTab(self._view)
        self._show_share_tab(self._view.details_share_tab)
        event.Skip()


class MainWindowListbook(wx.Listbook, Translator):
    """
    The layout of the main window, which initiates & contains all tabs.
    """

    def __init__(self, parent):
        wx.Listbook.__init__(self, parent, style=wx.BK_LEFT)

        # TODO: Set proper image for each tab
        image_list = wx.ImageList(64, 64)
        image_list.Add(wx.Image(resource_filename(
            'assets/images/settings.png')).ConvertToBitmap())
        self.AssignImageList(image_list)

        self.list_shares_tab = ListSharesTab(self)
        self.creation_shares_tab = None
        self.details_share_tab = None
        self.account_tab = AccountTab(self)
        self.general_settings_tab = GeneralSettingsTab(self)
        self.network_settings_tab = NetworkSettingsTab(self)
        self.advanced_settings_tab = AdvancedSettingsTab(self)

        self.AddPage(self.list_shares_tab,
                     N_("My Shares"), imageId=0)
        self.AddPage(self.account_tab,
                     N_("My Account"), imageId=0)
        self.AddPage(self.general_settings_tab,
                     N_("General Settings"), imageId=0)
        self.AddPage(self.network_settings_tab,
                     N_("Network Settings"), imageId=0)
        self.AddPage(self.advanced_settings_tab,
                     N_("Advanced Settings"), imageId=0)

        self.Bind(wx.EVT_LISTBOOK_PAGE_CHANGED, self.on_page_changed)
        self.on_page_changed()

    def on_page_changed(self, event=None):
        self.GetPage(self.GetSelection()).Show()
        self.GetParent().SetTitle(self.GetPageText(self.GetSelection()))
        self.GetParent().on_tab_changed(event)


def main():
    from ..common import config

    config.load()

    app = wx.App()
    win = MainWindow()

    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from ..api import Session, Container, TeamShare
    from ..common.future import wait_all
    from .form.members_share_form import MembersShareForm

    session = Session.create_session(
        'stran+20@bajoo.fr',
        'stran+20@bajoo.fr').result()

    def _on_shares_fetched(shares):
        _logger.debug("%d shares fetched", len(shares))
        win.load_shares(shares)

    def _on_request_shares(_event):
        return Container.list(session) \
            .then(_on_shares_fetched)

    def _on_request_share_details(event):
        share = event.share

        # Stimulate share data
        share.encrypted = True
        share.status = 'Synced'
        share.stats = {
            'folders': 4,
            'files': 168,
            'space': 260000000
        }

        def _on_members_listed(members):
            share.members = members
            win.set_share_details(share)

        share.list_members() \
            .then(_on_members_listed)

    def _on_request_config(_event):
        win.load_config(config)

    def _on_request_create_share(event):
        share_name = event.share_name
        members = event.members

        def on_members_added(__):
            win.on_new_share_created(None)

        def on_share_created(share):
            futures = []

            for member in members:
                permissions = members[member]
                permissions.pop('user')
                futures.append(share.add_member(member, permissions))

            return wait_all(futures).then(on_members_added)

        TeamShare.create(session, share_name) \
            .then(on_share_created)

    def _on_add_share_member(event):
        share = event.share
        email = event.user_email
        permission = event.permission

        def _on_member_added(__):
            win.on_share_member_added(share, email, permission)

        share.add_member(email, permission) \
            .then(_on_member_added)

    app.Bind(ListSharesTab.EVT_DATA_REQUEST,
             _on_request_shares)
    app.Bind(ListSharesTab.EVT_CONTAINER_DETAIL_REQUEST,
             _on_request_share_details)
    app.Bind(CreationShareTab.EVT_CREATE_SHARE_REQUEST,
             _on_request_create_share)
    app.Bind(GeneralSettingsTab.EVT_CONFIG_REQUEST,
             _on_request_config)
    app.Bind(NetworkSettingsTab.EVT_CONFIG_REQUEST,
             _on_request_config)
    app.Bind(AdvancedSettingsTab.EVT_CONFIG_REQUEST,
             _on_request_config)
    app.Bind(MembersShareForm.EVT_SUBMIT,
             _on_add_share_member)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
