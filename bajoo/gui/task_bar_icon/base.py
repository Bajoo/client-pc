# -*- coding: utf-8 -*-
"""Common interface and enumeration shared between TBI Controller and View."""


class WindowDestination(object):
    """Enum of destination accessible from the tray icon's menus."""
    HOME = 'HOME'
    SUSPEND = 'SUSPEND'
    SHARES = 'SHARES'
    INVITATION = 'INVITATION'
    SETTINGS = 'SETTINGS'
    ABOUT = 'ABOUT'
    DEV_CONTACT = 'DEV_CONTACT'
    CLIENT_SPACE = 'CLIENT_SPACE'
    ONLINE_HELP = 'ONLINE_HELP'


class ContainerStatus(object):
    """Different states possible for a container."""
    SYNC_DONE = 3
    SYNC_PROGRESS = 4
    SYNC_PAUSE = 5
    SYNC_STOP = 6
    SYNC_ERROR = 7


class TaskBarIconBaseView(object):
    """Abstract class for TaskBarIcon's view.

    Attributes:
        controller (TaskBarIconBaseController): TaskBarIcon controller.
    """
    def __init__(self, ctrl):
        self.controller = ctrl

    def set_app_status(self, app_status):
        """Set the general application status to display.

        Args:
            app_status (AppStatus): new status
        """
        raise NotImplementedError()

    def destroy(self):
        """Clean up all resources (Window, files, etc.) before deletion."""
        raise NotImplementedError()

    def notify_lang_change(self):
        """Update the view after a change of language setting."""
        raise NotImplementedError()

    # TODO: Use an observer pattern instead of updating the controller
    # Calling this method depends on the caller to have up-to-date information
    # each time the list changes. Beside that, the task bar icon must keep a
    # copy of the list.
    # The situation could be improved by giving a direct access to the
    # container list.
    def set_container_status_list(self, status_list):
        """Update the list of containers (and theirs status).

        Args:
            status_list (List[Tuple[unicode, unicode, ContainerStatus]]): list
                of containers. Each container is represented by a tuple of 3
                elements: its name, the absolute path of its local folder, and
                its status.
        """
        raise NotImplementedError()


class TaskBarIconBaseController(object):
    """Abstract class for TaskBarIcon's controller.

    Attributes:
        view (TaskBarIconBaseView): TaskBarIcon view;
    """

    def __init__(self, view):
        self.view = view

    def destroy(self):
        """Clean up all resources before deletion.

        The default behavior is to destroy the view.
        """
        self.view.destroy()

    # Controller actions triggered by the view

    def primary_action(self):
        """Apply the icon's primary action.

        It's usually triggered by a left click on the task bar icon.
        """
        raise NotImplementedError()

    def navigate_action(self, destination):
        """Open a window or a particular panel.

        This is called when the user enter in a menu and select an entry to
        navigate through the app.

        Args:
            destination (WindowDestination): target destination requested.
        """
        raise NotImplementedError()

    def open_container_action(self, folder_path):
        """Open the folder of a container.

        Args:
            folder_path (unicode): absolute path of the container.
        """
        raise NotImplementedError()

    def exit_action(self):
        """Properly exit the app."""
        raise NotImplementedError()
