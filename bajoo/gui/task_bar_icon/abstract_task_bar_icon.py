# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from os import path

from ...common.i18n import N_, _
from ...common.path import resource_filename
from ...common.util import open_folder


class MenuEntry(object):
    def __init__(self, menu_id, title, help_string=None):
        self.enabled = True
        self.menu_id = menu_id
        self.title = title
        self.help_string = help_string
        self.children = None
        self.icon = None
        self.event_handler = None


class AbstractTaskBarIcon(object):
    __metaclass__ = ABCMeta

    # Different event id
    OPEN_HOME = 1
    OPEN_SUSPEND = 2
    OPEN_SHARES = 3
    OPEN_INVITATION = 4
    OPEN_SETTINGS = 5
    OPEN_ABOUT = 6
    OPEN_DEV_CONTACT = 7
    OPEN_CLIENT_SPACE = 8
    OPEN_HELP = 9
    TASK_BAR_EXIT = 10

    # Different states possible for the App.
    NOT_CONNECTED = 1
    CONNECTION_PROGRESS = 2
    SYNC_DONE = 3
    SYNC_PROGRESS = 4
    SYNC_PAUSE = 5
    SYNC_STOP = 6
    SYNC_ERROR = 7

    _tooltips = {
        NOT_CONNECTED: N_('Not connected'),
        CONNECTION_PROGRESS: N_('Connection in progress...'),
        SYNC_DONE: N_('Sync up to date'),
        SYNC_PROGRESS: N_('Shares currently syncing...'),
        SYNC_PAUSE: N_('Synchronization suspended'),
        SYNC_STOP: N_('Synchronization is not active'),
        SYNC_ERROR: N_('An error happened :(')
    }

    def __init__(self):
        self._is_connected = False
        self._state = self.NOT_CONNECTED

        icon_path = 'assets/images/trayicon_status/%s.png'
        disconnected_icon = resource_filename(icon_path % 'disconnected')
        connecting_icon = resource_filename(icon_path % 'connecting')
        sync_icon = resource_filename(icon_path % 'sync')
        paused_icon = resource_filename(icon_path % 'paused')
        progress_icon = resource_filename(icon_path % 'progress')

        icon_container = 'assets/images/container_status/%s.png'
        container_status_done = resource_filename(icon_container % 'synced')
        container_status_progress = resource_filename(
            icon_container % 'progress')
        container_status_pause = resource_filename(icon_container % 'paused')
        container_status_stop = resource_filename(icon_container % 'stopped')
        container_status_error = resource_filename(icon_container % 'error')

        self._icons = {
            self.NOT_CONNECTED: disconnected_icon,
            self.CONNECTION_PROGRESS: connecting_icon,
            self.SYNC_DONE: sync_icon,
            self.SYNC_PROGRESS: progress_icon,
            self.SYNC_PAUSE: paused_icon
        }

        self._container_icons = {
            self.SYNC_DONE: container_status_done,
            self.SYNC_PROGRESS: container_status_progress,
            self.SYNC_PAUSE: container_status_pause,
            self.SYNC_STOP: container_status_stop,
            self.SYNC_ERROR: container_status_error
        }

        self._container_menu = None
        self.online_menu = self._generate_online_items()
        self.offline_menu = self._generate_offline_items()
        self.generic_menu = self._generate_generic_menu()

    def _generate_online_items(self):
        menus = []

        menus.append(None)  # menu separator

        m = MenuEntry(-1, N_('Bajoo folder'))
        sub_m = MenuEntry(-1, N_("Looks like you don't\nhave any share"))
        sub_m.enabled = False
        m.children = [sub_m]
        self._container_menu = m
        menus.append(m)

        m = MenuEntry(self.OPEN_SUSPEND, N_('Suspend synchronization'))
        m.enabled = False
        menus.append(m)

        menus.append(MenuEntry(self.OPEN_SHARES, N_('Manage my folders...')))

        menus.append(None)  # menu separator

        m = MenuEntry(self.OPEN_CLIENT_SPACE, N_('My client space'))
        m.enabled = False
        menus.append(m)

        m = MenuEntry(self.OPEN_INVITATION, N_('Invite a friend on Bajoo'))
        m.enabled = False
        menus.append(m)

        menus.append(MenuEntry(self.OPEN_HELP, N_('Online help')))

        menus.append(None)  # menu separator

        m = MenuEntry(self.OPEN_SETTINGS, N_('Settings ...'))
        menus.append(m)

        return menus

    def _generate_offline_items(self):
        menus = []
        m = MenuEntry(self.OPEN_HOME,
                      N_('Login window'),
                      N_('Open the login and registration window'))
        menus.append(m)

        return menus

    def _generate_generic_menu(self):
        menus = []
        menus.append(MenuEntry(self.OPEN_ABOUT, N_('About Bajoo')))
        menus.append(MenuEntry(self.OPEN_DEV_CONTACT, N_('Report a problem')))
        menus.append(None)  # menu separator
        menus.append(MenuEntry(self.TASK_BAR_EXIT,
                               N_('Quit'),
                               N_('Quit Bajoo')))
        return menus

    def _getMenuItems(self):
        if self._is_connected:
            menus = list(self.online_menu)
        else:
            menus = list(self.offline_menu)

        menus.extend(self.generic_menu)
        return menus

    def set_state(self, state):
        """Set the general app state.

        The icon and its tooltip will change according to the state.

        Args:
            state: must be one of 'NOT_CONNECTED', 'CONNECTION_PROGRESS',
                'SYNC_DONE', 'SYNC_PROGRESS' or 'SYNC_PAUSE'
        """

        self._state = state
        self._is_connected = state is not self.NOT_CONNECTED
        self.set_icon(self._icons[state], _(self._tooltips[state]))

    def set_container_status_list(self, status_list):
        if (self._container_menu is None or
           status_list is None or
           len(status_list) == 0):
            return

        if self._container_menu.children is not None:
            del self._container_menu.children[:]
        else:
            self._container_menu.children = []

        shares_menu = MenuEntry(-1, _('Shares folder'))
        shares_menu.children = []

        my_bajoo_count = 0
        for name, fpath, status in status_list:
            # TODO: Find a way to distinguish 'MyBajoo' folder and a
            # TODO: shared folder named 'MyBajoo'
            if name == 'MyBajoo':
                parent_menu = self._container_menu
                my_bajoo_count += 1
            else:
                parent_menu = shares_menu

            menu = MenuEntry(-1, name)
            menu.enabled = bool(fpath) and path.exists(fpath)
            menu.icon = self._container_icons[status]
            parent_menu.children.append(menu)

            def open_container(_evt, folder_path=fpath):
                if path.exists(folder_path):
                    open_folder(folder_path)

                return False

            menu.event_handler = open_container

        # if not status_list or len(status_list) == my_bajoo_count:
        if len(shares_menu.children) == 0:
            menu = MenuEntry(-1, _("Looks like you don't\nhave any share"))
            menu.enabled = False
            shares_menu.children.append(menu)

        self._container_menu.children.append(shares_menu)

    @abstractmethod
    def set_icon(self, icon, tooltip=None):
        pass  # ABSTRACT
