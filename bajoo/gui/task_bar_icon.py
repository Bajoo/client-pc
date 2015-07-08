# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent

from ..common.i18n import N_, _
from ..common.path import resource_filename


class TaskBarIcon(wx.TaskBarIcon):
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

    ExitEvent, EVT_EXIT = NewCommandEvent()
    OpenWindowEvent, EVT_OPEN_WINDOW = NewCommandEvent()

    _tooltips = {
        NOT_CONNECTED: N_('Not connected'),
        CONNECTION_PROGRESS: N_('Connection in progress...'),
        SYNC_DONE: N_('Sync up to date'),
        SYNC_PROGRESS: N_('Shares currently syncing...'),
        SYNC_PAUSE: N_('Synchronization suspended')
    }

    def __init__(self):
        wx.TaskBarIcon.__init__(self)

        self._is_connected = False

        # TODO: use different icons.
        icon_path = resource_filename('assets/icons/bajoo.ico')

        self._icons = {
            self.NOT_CONNECTED: wx.Icon(icon_path),
            self.CONNECTION_PROGRESS: wx.Icon(icon_path),
            self.SYNC_DONE: wx.Icon(icon_path),
            self.SYNC_PROGRESS: wx.Icon(icon_path),
            self.SYNC_PAUSE: wx.Icon(icon_path)
        }

        self.set_state(self.NOT_CONNECTED)

        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self._open_window)
        self.Bind(wx.EVT_MENU, self._open_window, id=wx.ID_HOME)
        self.Bind(wx.EVT_MENU,
                  lambda _evt: wx.PostEvent(self, self.ExitEvent(-1)),
                  id=wx.ID_EXIT)

    def _open_window(self, event):
        wx.PostEvent(self, self.OpenWindowEvent(-1))

    def CreatePopupMenu(self):
        menu = wx.Menu()
        if self._is_connected:
            pass
        else:
            menu.Append(wx.ID_HOME, _('Login window'),
                        _('Open the login and registration window'))
        menu.Append(wx.ID_EXIT, _('Quit'), _('Quit Bajoo'))
        return menu

    def set_state(self, state):
        """Set the general app state.

        The icon and its tooltip will change according to the state.

        Args:
            state: must be one of 'NOT_CONNECTED', 'CONNECTION_PROGRESS',
                'SYNC_DONE', 'SYNC_PROGRESS' or 'SYNC_PAUSE'
        """

        self._is_connected = state is not self.NOT_CONNECTED

        self.SetIcon(self._icons[state], tooltip=_(self._tooltips[state]))
