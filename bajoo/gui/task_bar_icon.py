# -*- coding: utf-8 -*-

import webbrowser
import wx
from wx.lib.newevent import NewCommandEvent

from ..common.i18n import N_, _
from ..common.path import resource_filename
from .translator import Translator


class TaskBarIcon(wx.TaskBarIcon, Translator):
    """Task bar icon of the Bajoo app

    The trayicon send an ExitEvent when the user want to quit.
    When the user click on a menu to open a window, an event OpenWindowEvent
    is emitted.

    """

    # Different states possible for the App.
    NOT_CONNECTED = 1
    CONNECTION_PROGRESS = 2
    SYNC_DONE = 3
    SYNC_PROGRESS = 4
    SYNC_PAUSE = 5

    # OpenWindowEvent(target=OPEN_HOME)
    ExitEvent, EVT_EXIT = NewCommandEvent()
    OpenWindowEvent, EVT_OPEN_WINDOW = NewCommandEvent()

    # Possible values for OpenWindowEvent
    OPEN_HOME = 1
    OPEN_SUSPEND = 2
    OPEN_SHARES = 3
    OPEN_INVITATION = 4
    OPEN_SETTINGS = 5
    OPEN_ABOUT = 6

    # IDs for menu entries
    ID_SUSPEND_SYNC = wx.NewId()
    ID_MANAGE_SHARES = wx.NewId()
    ID_CLIENT_SPACE = wx.NewId()
    ID_INVITATION = wx.NewId()
    ID_HELP = wx.NewId()
    ID_SETTINGS = wx.NewId()

    _tooltips = {
        NOT_CONNECTED: N_('Not connected'),
        CONNECTION_PROGRESS: N_('Connection in progress...'),
        SYNC_DONE: N_('Sync up to date'),
        SYNC_PROGRESS: N_('Shares currently syncing...'),
        SYNC_PAUSE: N_('Synchronization suspended')
    }

    def __init__(self):
        wx.TaskBarIcon.__init__(self)
        Translator.__init__(self)

        self._is_connected = False
        self._state = self.NOT_CONNECTED

        icon_path = 'assets/icons/trayicon-%s.png'
        disconnected_icon = resource_filename(icon_path % 'connecting')
        connecting_icon = resource_filename(icon_path % 'connecting')
        sync_icon = resource_filename(icon_path % 'sync')
        paused_icon = resource_filename(icon_path % 'paused')
        progress_icon = resource_filename(icon_path % 'progress')

        self._icons = {
            self.NOT_CONNECTED: wx.Icon(disconnected_icon),
            self.CONNECTION_PROGRESS: wx.Icon(connecting_icon),
            self.SYNC_DONE: wx.Icon(sync_icon),
            self.SYNC_PROGRESS: wx.Icon(progress_icon),
            self.SYNC_PAUSE: wx.Icon(paused_icon)
        }

        self.set_state(self.NOT_CONNECTED)
        self.register_i18n(
            lambda txt: self.SetIcon(self._icons[self._state], tooltip=txt),
            self._tooltips[self._state])

        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self._open_window)
        self.Bind(wx.EVT_MENU,
                  lambda _evt: wx.PostEvent(self, self.ExitEvent(-1)),
                  id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self._open_window)

    def _open_window(self, event):
        mapping_open_evt = {
            self.ID_SUSPEND_SYNC: self.OPEN_SUSPEND,
            self.ID_MANAGE_SHARES: self.OPEN_SHARES,
            self.ID_SETTINGS: self.OPEN_SETTINGS,
            self.ID_INVITATION: self.OPEN_INVITATION,
            wx.ID_ABOUT: self.OPEN_ABOUT,
            wx.ID_HOME: self.OPEN_HOME,
            -1: self.OPEN_HOME  # left click on tray icon
        }

        if event.GetId() in mapping_open_evt:
            wx.PostEvent(self, self.OpenWindowEvent(
                -1, target=mapping_open_evt[event.GetId()]))
        elif event.GetId() == self.ID_HELP:
            # TODO: set real URL
            webbrowser.open('https://www.bajoo.fr/help')
        elif event.GetId() == self.ID_CLIENT_SPACE:
            # TODO: set real URL
            webbrowser.open('https://www.bajoo.fr/client_space')
        else:
            event.Skip()

    def CreatePopupMenu(self):
        menu = wx.Menu()
        if self._is_connected:
            list_shares_menu = wx.Menu()
            # TODO: list Bajoo shares in the menu.
            list_shares_menu.Append(
                -1, _("Looks like you don't\nhave any share")).Enable(False)

            # TODO: add account information.
            menu.AppendSeparator()
            menu.AppendMenu(-1, _('Shares folder'), list_shares_menu)
            menu.Append(self.ID_SUSPEND_SYNC, _('Suspend synchronization'))
            menu.Append(self.ID_SETTINGS, _('Manage my shares...'))
            menu.AppendSeparator()
            menu.Append(self.ID_CLIENT_SPACE, _('My client space'))
            menu.Append(self.ID_INVITATION, _('Invite a friend on Bajoo'))
            menu.Append(self.ID_HELP, _('Online help'))
            menu.AppendSeparator()
            menu.Append(self.ID_SETTINGS, _('Settings ...'))
        else:
            menu.Append(wx.ID_HOME, _('Login window'),
                        _('Open the login and registration window'))
        menu.Append(wx.ID_ABOUT, _('About Bajoo'))
        menu.AppendSeparator()
        menu.Append(wx.ID_EXIT, _('Quit'), _('Quit Bajoo'))
        return menu

    def set_state(self, state):
        """Set the general app state.

        The icon and its tooltip will change according to the state.

        Args:
            state: must be one of 'NOT_CONNECTED', 'CONNECTION_PROGRESS',
                'SYNC_DONE', 'SYNC_PROGRESS' or 'SYNC_PAUSE'
        """

        self._state = state
        self._is_connected = state is not self.NOT_CONNECTED
        self.SetIcon(self._icons[state], tooltip=self._tooltips[state])
