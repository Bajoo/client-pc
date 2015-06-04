# -*- coding: utf-8 -*-

import logging
import wx

from .common.path import get_data_dir
from .connection_registration_process import connect_or_register

_logger = logging.getLogger(__name__)


class BajooApp(wx.App):
    """Main class who start and manages the user interface.

    This is the first class created, just after the loading of configuration
    and the log initialization. It contains the global process of organization
    the different actions to perform and the user interface.

    All algorithms specific to this client (ie: not in the work layer) are cut
    into specific process functions. The BajooApp instance will call these
    functions and provides them appropriate user interface handlers. It will
    chain the different operations appropriately.

    The BajooApp will also manage the top-level windows life, and will catch
    the global user events (like quit).

    Call ``app.MainLoop()`` will start the event loop. The graphics elements
    will be displayed and the connexion process will start.
    """

    def __init__(self):
        # Don't redirect the stdout in a windows.
        wx.App.__init__(self, redirect=False)

    def _ensures_single_instance_running(self):
        """Check that only one instance of Bajoo is running per user.

        If another instance is running, an explicative box is displayed.

        Returns:
            boolean: True if no other instance is actually running;
                False otherwise.
        """

        # Using GetUserId() allow two different users to have
        # theirs own Bajoo instance.
        app_name = "Bajoo-%s" % wx.GetUserId()

        # Note: the checker must be owned by ``self``, to stay alive until the
        # end of the program.
        self._checker = wx.SingleInstanceChecker(app_name, path=get_data_dir())
        if self._checker.IsAnotherRunning():
            _logger.info('Prevents the user to start a second Bajoo instance.')

            wx.MessageBox("Another instance of Bajoo is actually running.\n"
                          "You can't open Bajoo twice.",
                          caption="Bajoo already started")
            return False
        return True

    def OnInit(self):

        if not self._ensures_single_instance_running():
            return False

        frame = wx.Frame(None, wx.ID_ANY, "Hello World")
        frame.Show(True)
        self.SetTopWindow(frame)

        # TODO: Create the TrayIcon

        return True

    def OnEventLoopEnter(self):
        """Start the event loop, and the connection process."""
        # TODO: pass correct argument
        connect_or_register(None)
        # TODO: .then(StartSyncProcess)
