# -*- coding: utf-8 -*-

import logging
import os.path
import webbrowser
import wx
from ...app_status import AppStatus
from ...common.i18n import _
from ...common.signal import Signal
from ...common.util import open_folder
from ..enums import WindowDestination

_logger = logging.getLogger(__name__)


class TaskBarIconController(object):
    """Task Bar Icon Controller.

    The general status and the list of containers must be updated, by using
    `set_app_status` and  `set_container_status_list`.
    Also, the controller expects `notify_lang_change` to be called in case of
    language change.

    Attributes:
        navigate (Signal): Signal fired with the user want to navigate to a
            window or a screen. It gives the destination (Navigation value) as
            fire value.
        exit_app (Signal): Signal fired without argument, when the user wants
            to quit Bajoo.
    """

    def __init__(self, view_factory):
        """TaskBarIcon Controller constructor

        Args:
            view_factory (type): View class. Will be instantiated at start.

        Attributes:
            view (TaskBarIconBaseView): TaskBarIcon view
        """
        self.view = view_factory(self)

        self._is_connected = False

        self.navigate = Signal()
        self.exit_app = Signal()

        self.view.set_app_status(AppStatus.NOT_CONNECTED)

    def set_app_status(self, status):
        """Update the application status.

        Args:
            status (AppStatus): new status
        """
        self._is_connected = status is not AppStatus.NOT_CONNECTED
        self.view.set_app_status(status)

    def set_container_status_list(self, status_list):
        """Update the container list (and theirs status).

        Args:
            status_list (List[Tuple[unicode, unicode, ContainerStatus]]): list
                of containers. Each container is represented by a tuple of 3
                elements: its name, the absolute path of its local folder, and
                its status.
        """
        self.view.set_container_status_list(status_list)

    def notify_lang_change(self):
        """Rebuild the GUI after a language change."""
        self.view.notify_lang_change()

    def primary_action(self):
        """Apply the icon's primary action.

        It's usually triggered by a left click on the task bar icon.
        """
        _logger.debug('Execute TaskBarIcon main action')

        # TODO: remove this ugly dependency to BajooApp
        if wx.GetApp().user_profile is not None:
            # User connected, open the root folder
            open_folder(wx.GetApp().user_profile.root_folder_path)
        else:
            # User not connected, open the connection window
            self.navigate.fire(WindowDestination.HOME)

    def navigate_action(self, destination):
        """Open a window or a particular panel.

        This is called when the user enter in a menu and select an entry to
        navigate through the app.

        Args:
            destination (WindowDestination): target destination requested.
        """
        _logger.debug('Navigate action to %s', destination)

        web_navigation_mapping = {
            WindowDestination.CLIENT_SPACE:
                'https://www.bajoo.fr/client_space',
            WindowDestination.ONLINE_HELP: _('https://www.bajoo.fr/help'),
            WindowDestination.BAJOO_DROP: 'https://drop.bajoo.fr'
        }

        if destination in web_navigation_mapping:
            webbrowser.open(web_navigation_mapping[destination])
        else:
            self.navigate.fire(destination)

    def open_container_action(self, folder_path):
        """Open the folder of a container.

        Args:
            folder_path (unicode): absolute path of the container.
        """
        _logger.debug(u'Open container with path "%s"', folder_path)

        # TODO: We should receive a container (or its ID) instead of the path.
        if os.path.exists(folder_path):
            open_folder(folder_path)

    def exit_action(self):
        """Properly exit the app."""
        _logger.debug('Exit action')
        self.exit_app.fire()

    def destroy(self):
        """Clean up all resources before deletion."""
        self.view.destroy()
        self.navigate.disconnect_all()
        self.exit_app.disconnect_all()
