# -*- coding: utf-8 -*-

import logging

import wx

from ..common.i18n import _
from ..common.path import resource_filename
from ..gui.event_promise import ensure_gui_thread
from .tab import ListSharesTab
from .tab import CreationShareTab
from .tab import DetailsShareTab
from .tab import AccountTab
from .tab import SettingsTab
from .translator import Translator

_logger = logging.getLogger(__name__)


class MainWindow(wx.Frame, Translator):
    """Main window accessible when the user is connected.

    It contains different tabs (from the `bajoo.gui.tab.*` modules) allowing
    to do almost all Bajoo operations.

    Some actions may generate "temporary" tabs. Theses tabs have no menu entry
    and so are not directly accessible to the end user. They are located after
    the normal tabs.
    """
    LIST_SHARES_TAB = 0
    ACCOUNT_TAB = 1
    SETTINGS_TAB = 2

    def __init__(self):
        wx.Frame.__init__(self, parent=None, size=(800, 600))
        Translator.__init__(self)

        self.SetMinSize((800, 600))
        self._view = MainWindowListbook(self)

        icon_path = resource_filename('assets/window_icon.png')
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

        self.show_list_shares_tab()

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self._view.notify_lang_change()

    def _show_tab(self, tab_index, data=None):
        # Remove all temperatory tabs
        while self._view.GetPageCount() > 3:
            self._view.DeletePage(3)

        self._view.details_share_tab = None
        self._view.creation_shares_tab = None

        self._view.SetSelection(tab_index)

        if tab_index == MainWindow.LIST_SHARES_TAB:
            if data.get('refresh', False):
                self._view.list_shares_tab.send_data_request()

    def _show_share_tab(self, share_tab, title=''):
        """
        We have 3 share-related tabs,
        this function will display the share_tab at first place,
        & hide the 2 other ones.
        """
        if self._view.GetPageCount() > 3:
            self._view.DeletePage(3)
            self._view.InsertPage(3, share_tab, title, select=True)
        else:
            self._view.AddPage(share_tab, title, select=True)

    def on_tab_changed(self, event):
        if hasattr(self, '_view') \
                and self._view.GetSelection() < 3:
            while self._view.GetPageCount() > 3:
                self._view.DeletePage(3)

            self._view.details_share_tab = None
            self._view.creation_shares_tab = None

    @ensure_gui_thread
    def show_account_tab(self):
        """Make the account tab shown on top."""
        self._show_tab(MainWindow.ACCOUNT_TAB)

    @ensure_gui_thread
    def show_list_shares_tab(self, refresh=True):
        """Make the share list tab shown on top."""
        self._show_tab(MainWindow.LIST_SHARES_TAB, {'refresh': refresh})

    @ensure_gui_thread
    def show_creation_shares_tab(self):
        """Make the creation share tab shown on top."""
        self._show_share_tab(self._view.creation_shares_tab)

    @ensure_gui_thread
    def show_details_share_tab(self, share):
        self._show_share_tab(self._view.details_share_tab)
        self._view.details_share_tab.set_data(share)

    def show_settings_tab(self):
        """Make the Settings tab shown on top."""
        self._show_tab(MainWindow.SETTINGS_TAB)

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
    def load_shares(self, shares, success_msg=None, error_msg=None,
                    show_tab=True):
        """
        load & display the shares on share list tab.

        Args:
            shares: list of LocalContainer
        """
        self._view.list_shares_tab.set_data({
            'shares': shares,
            'success_msg': success_msg,
            'error_msg': error_msg
        })

        if show_tab:
            self.show_list_shares_tab(False)

    @ensure_gui_thread
    def set_share_details(self, share_details):
        if self._view.details_share_tab:
            self._view.details_share_tab.set_data(share_details)

    @ensure_gui_thread
    def load_config(self, config):
        self._view.settings_tab.load_config(config)

    @ensure_gui_thread
    def on_new_share_created(self, new_share):
        self.show_list_shares_tab()

    @ensure_gui_thread
    def on_share_member_added(self, share, email, permission, message=None):
        if self._view.details_share_tab:
            self._view.details_share_tab.enable()

            if self._view.details_share_tab.get_displayed_share() is share \
                    and email is not None:
                self._view.details_share_tab.add_member_view(
                    email, permission)

                # Show message if neccessary
                if message:
                    self._view.details_share_tab.show_message(message)
            else:
                # Show error message if neccessary
                if message:
                    self._view.details_share_tab.show_error_message(message)

    def on_share_member_removed(self, share, email, message=None):
        """
        React when a member has been removed from the share.

        Args:
            share: the share from which the member has been removed.
            email: None if the removal has failed, otherwise email
                of the member removed.
        """
        if self._view.details_share_tab:
            self._view.details_share_tab.enable()

            if self._view.details_share_tab.get_displayed_share() is share \
                    and email is not None:
                self._view.details_share_tab.set_data(share)

                # Show message if neccessary
                if message:
                    self._view.details_share_tab.show_message(message)
            else:
                # Show error message if neccessary
                if message:
                    self._view.details_share_tab.show_error_message(message)

    @ensure_gui_thread
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

    @ensure_gui_thread
    def on_password_changed(self):
        if self._view.account_tab:
            self._view.account_tab.on_password_change_success()

    @ensure_gui_thread
    def on_password_change_error(self, message):
        if self._view.account_tab:
            self._view.account_tab.show_password_change_error(message)

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
        Translator.__init__(self)

        image_list = wx.ImageList(64, 64)
        for img_path in ('assets/images/menu_my_shares.png',
                         'assets/images/menu_user.png',
                         'assets/images/menu_settings.png'):
            img = wx.Image(resource_filename(img_path)).Rescale(64, 64)
            image_list.Add(img.ConvertToBitmap())
        self.AssignImageList(image_list)

        self.list_shares_tab = ListSharesTab(self)
        self.creation_shares_tab = None
        self.details_share_tab = None
        self.account_tab = AccountTab(self)
        self.settings_tab = SettingsTab(self)

        self.AddPage(self.list_shares_tab,
                     _("My Shares"), imageId=0)
        self.AddPage(self.account_tab,
                     _("My Account"), imageId=1)
        self.AddPage(self.settings_tab, _("Settings"), imageId=2)

        self.Bind(wx.EVT_LISTBOOK_PAGE_CHANGED, self.on_page_changed)
        self.on_page_changed()

    def notify_lang_change(self):
        Translator.notify_lang_change(self)

        self.SetPageText(0, _("My Shares"))
        self.SetPageText(1, _("My Account"))
        self.SetPageText(2, _("Settings"))

        # Notify permanent tabs
        self.account_tab.notify_lang_change()
        self.list_shares_tab.notify_lang_change()
        self.settings_tab.notify_lang_change()

        # Notify temporary tabs.
        # Normally we don't have to do this because
        # when user changes the language,
        # it means that the "General settings" tab is currently shown,
        # and the temporary tabs are destroyed.
        # This is done just in case, so we can be assured.
        if self.creation_shares_tab:
            self.creation_shares_tab.notify_lang_change()

        if self.details_share_tab:
            self.details_share_tab.notify_lang_change()

        # Change the title of the window
        self.GetParent().SetTitle(self.GetPageText(self.GetSelection()))

    def on_page_changed(self, event=None):
        self.GetPage(self.GetSelection()).Show()

        if isinstance(self.GetPage(self.GetSelection()), CreationShareTab):
            self.GetParent().SetTitle(_('Create new share'))
        elif isinstance(self.GetPage(self.GetSelection()), DetailsShareTab):
            self.GetParent().SetTitle(_('Folder details'))
        else:
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
    from ..promise import Promise
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

            return Promise.all(futures).then(on_members_added)

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
    app.Bind(SettingsTab.EVT_CONFIG_REQUEST, _on_request_config)
    app.Bind(MembersShareForm.EVT_SUBMIT,
             _on_add_share_member)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
