# -*- coding: utf-8 -*-


class WindowDestination(object):
    """Enum of destination accessible from the tray icon's menus.

    An entry can represent a Window, a particular tab from a window, or an
    external URL.
    """
    HOME = 'HOME'
    SUSPEND = 'SUSPEND'
    SHARES = 'SHARES'
    INVITATION = 'INVITATION'
    SETTINGS = 'SETTINGS'
    ABOUT = 'ABOUT'
    DEV_CONTACT = 'DEV_CONTACT'
    CLIENT_SPACE = 'CLIENT_SPACE'
    ONLINE_HELP = 'ONLINE_HELP'
    BAJOO_DROP = 'BAJOO_DROP'


class ContainerStatus(object):
    """Different states possible for a container."""
    SYNC_DONE = 3
    SYNC_PROGRESS = 4
    SYNC_PAUSE = 5
    SYNC_STOP = 6
    SYNC_ERROR = 7
