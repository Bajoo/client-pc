# -*- coding: utf-8 -*-
"""Raw data, common to all TaskBarIcon views.

It includes mapping between enumerations and view-related data: path of icons
files, context messages for status, etc.

Also, it includes a framework-agnostic representation of the TaskBarIcon's menu
and its sub-menus.

Attributes:
    app_status_to_icon_files (Dict[AppStatus, unicode]): mapping between
        AppStatus and a corresponding icon file path.
    container_status_to_icon_files (Dict[ContainerStatus, unicode]): mapping
        between ContainerStatus and a corresponding icon file path.
    app_status_to_tooltips (Dict[AppStatus, str]: mapping between AppStatus
        values and small messages describing the status.
        The messages are marked for translation, but not translated.
"""

import os.path
from ...app_status import AppStatus
from ...common.i18n import N_, _
from ...common.path import resource_filename
from .base import ContainerStatus, WindowDestination


class TaskBarIconAction(object):
    """Enum of action's type that can be triggered by a TBI menu item."""
    OPEN_CONTAINER = 'OPEN_CONTAINER'
    NAVIGATE = 'NAVIGATE'
    EXIT = 'EXIT'


_app_status_icon_base_path = 'assets/images/trayicon_status/%s.png'
_container_status_icon_base_path = 'assets/images/container_status/%s.png'


app_status_to_icon_files = {
    status: resource_filename(_app_status_icon_base_path % name)
    for (status, name) in {
        AppStatus.NOT_CONNECTED: 'disconnected',
        AppStatus.CONNECTION_IN_PROGRESS: 'connecting',
        AppStatus.SYNC_DONE: 'sync',
        AppStatus.SYNC_IN_PROGRESS: 'progress',
        AppStatus.SYNC_PAUSED: 'paused',
        # TODO: either add an icon for this, or remove the status.
        # AppStatus.SYNC_STOPPED: '??????'
        # AppStatus.SYNC_IN_ERROR: '??????'
    }.items()
    }

container_status_to_icon_files = {
    status: resource_filename(_container_status_icon_base_path % name)
    for (status, name) in {
        ContainerStatus.SYNC_DONE: 'synced',
        ContainerStatus.SYNC_PROGRESS: 'progress',
        ContainerStatus.SYNC_PAUSE: 'paused',
        ContainerStatus.SYNC_STOP: 'stopped',
        ContainerStatus.SYNC_ERROR: 'error'
    }.items()
    }

app_status_to_tooltips = {
    AppStatus.NOT_CONNECTED: N_('Not connected'),
    AppStatus.CONNECTION_IN_PROGRESS: N_('Connection in progress...'),
    AppStatus.SYNC_DONE: N_('Sync up to date'),
    AppStatus.SYNC_IN_PROGRESS: N_('Shares currently syncing...'),
    AppStatus.SYNC_PAUSED: N_('Synchronization suspended'),
    AppStatus.SYNC_STOPPED: N_('Synchronization is not active'),
    AppStatus.SYNC_IN_ERROR: N_('An error occurred :(')
}


class MenuEntry(object):
    """Model (tree node) of a menu entry or a sub-menu.

    Each MenuEntry can be either a "final" entry (leaf tree) or a sub-menu.
    The only difference is the presence of children. If an entry has no child
    (`len(entry.children) == 0`), then it's a leaf.

    Notes:
        Sub-menus (entries with children) can't have an action.

    Attributes:
        title (str): text of the menu. This text is localized.
        enabled (bool): state of the menu entry. A disabled entry is usually
            displayed grayed, and its actions can be triggered.
        children (List[MenuEntry]): list of entries children, member of the
            sub-menu. Can contain MenuEntry.Separator.
        icon (Optional[unicode]): if set, path of an icon file.
        action (optional[TaskBarIconAction]): if set, action to apply (to
            transmit to the controller) when the menu entry event is triggered.
        target (Optional[Any]): "argument" used by the action.

    Class attributes:
        Separator (MenuEntry.Separator): Special const object, representing a
            separator entry (in a menu).
    """

    Separator = object()

    def __init__(self, title, enabled=True, icon=None, action=None,
                 target=None):
        """MenuEntry constructor

        Args:
            title (str, optional): text of the menu.
            enabled(bool, optional): state of the menu entry. Default to True.
            icon (unicode, optional): if set, path of an icon file.
            action (TaskBarIconAction, optional): if `target` is set, default
                to `TaskBarIconAction.NAVIGATE`. Otherwise, default to None.
            target (Any, optional): target argument, used by the action. If a
                target is set without explicit action, the action will be set
                to `TaskBarIconAction.NAVIGATE`.
        """
        self.title = title
        self.enabled = enabled
        self.icon = icon
        self.action = action
        self.target = target
        self.children = []

        if action is None and target is not None:
            self.action = TaskBarIconAction.NAVIGATE

    @classmethod
    def make_menu(cls, is_authenticated, shares_list):
        """Generate the task bar icon menu representation.

        Args:
            is_authenticated (bool):
            shares_list (List[Tuple[unicode, unicode, ContainerStatus]]): list
                of containers. Each container is represented by a tuple of 3
                elements: its name, the absolute path of its local folder, and
                its status.
        Returns:
            List[MenuEntry]: entries of task bar icon menu.
        """
        if is_authenticated:
            base_menu = cls._authenticated_menu_part(shares_list)
        else:
            base_menu = cls._unauthenticated_menu_part()
        return base_menu + cls._generic_menu_part()

    @classmethod
    def _unauthenticated_menu_part(cls):
        """TaskBarIcon's menu part, only present when user is not logged."""
        return [
            cls(_('Login window'), target=WindowDestination.HOME)
        ]

    @classmethod
    def _authenticated_menu_part(cls, container_status_list):
        if container_status_list is None:
            container_status_list = []

        container_menu = MenuEntry(_('Bajoo folder'))
        container_menu.children = cls._container_list_submenu(
            container_status_list)

        return [
            container_menu,
            cls(_('Suspend synchronization'), enabled=False,
                target=WindowDestination.SUSPEND),
            cls(_('Manage my folders...'), target=WindowDestination.SHARES),
            cls.Separator,
            cls(_('My client space'), enabled=False,
                target=WindowDestination.CLIENT_SPACE),
            cls(_('Invite a friend on Bajoo'), enabled=False,
                target=WindowDestination.INVITATION),
            cls(_('Online help'), target=WindowDestination.ONLINE_HELP),
            cls.Separator,
            cls(_('Settings ...'), target=WindowDestination.SETTINGS)
        ]

    @classmethod
    def _container_list_submenu(cls, container_status_list):

        container_menu_list = []
        shares_menu_list = []

        for name, fpath, status in container_status_list:
            # TODO: Find a way to distinguish 'MyBajoo' folder and a
            # TODO: shared folder named 'MyBajoo'
            if name == 'MyBajoo':
                menu_list = container_menu_list
            else:
                menu_list = shares_menu_list

            menu = MenuEntry(name,
                             # TODO: add "reachable" property: The view should
                             # not use os.path.
                             enabled=(bool(fpath) and os.path.exists(fpath)),
                             icon=container_status_to_icon_files[status],
                             action=TaskBarIconAction.OPEN_CONTAINER,
                             target=fpath)

            menu_list.append(menu)

        if not shares_menu_list:
            shares_menu_list = [
                MenuEntry(_("Looks like you don't\nhave any share"),
                          enabled=False)
            ]

        shares_menu = MenuEntry(_('Shares folder'))
        shares_menu.children = shares_menu_list

        return container_menu_list + [
            shares_menu
        ]

    @classmethod
    def _generic_menu_part(cls):
        """Part of the TaskBarIcon's menu that's always present."""
        return [
            cls(_('About Bajoo'), target=WindowDestination.ABOUT),
            cls(_('Report a problem'), target=WindowDestination.DEV_CONTACT),
            cls.Separator,
            cls(_('Quit'), action=TaskBarIconAction.EXIT)
        ]
