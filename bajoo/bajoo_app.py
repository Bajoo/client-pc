# -*- coding: utf-8 -*-

import logging
from .gui import wx_compat  # noqa
import wx
from wx.lib.softwareupdate import SoftwareUpdate

from .common import config
from .common.path import get_data_dir
from .connection_registration_process import connect_or_register
from .container_sync_pool import ContainerSyncPool
from .dynamic_container_list import DynamicContainerList
from .gui.event_future import ensure_gui_thread
from .gui.home_window import HomeWindow
from .gui.main_window import MainWindow
from .gui.message_notifier import MessageNotifier
from .gui.proxy_window import EVT_PROXY_FORM
from .gui.task_bar_icon import TaskBarIcon

_logger = logging.getLogger(__name__)


class BajooApp(wx.App, SoftwareUpdate):
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

    Attributes:
        _checker (wx.SingleInstanceChecker): Mutex used to avoid starting bajoo
            twice at the same time.
        _home_window (HomeWindow): if exists, the main window in not connected
            mode. This attribute is used to gives it the focus when the user
            interacts with the tray icon.
    """

    def __init__(self):
        self._checker = None
        self._home_window = None
        self._main_window = None
        self._task_bar_icon = None
        self._notifier = None
        self._session = None
        self._container_list = None
        self._container_sync_pool = ContainerSyncPool()

        # Don't redirect the stdout in a windows.
        wx.App.__init__(self, redirect=False)

        self.SetAppName("Bajoo")

        # TODO: Set real value for production.
        base_url = "http://192.168.1.120:8000"
        self.InitUpdates(base_url, base_url + "/" + 'ChangeLog.txt')
        self.AutoCheckForUpdate(0)

        # Note: the loop event only works if at least one wx.Window exists. As
        # wx.TaskBarIcon is not a wx.Window, we need to keep this unused frame.
        self._dummy_frame = wx.Frame(None)

        self.Bind(EVT_PROXY_FORM, self._on_proxy_config_changes)

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

    def _on_proxy_config_changes(self, event):
        config.set('proxy_mode', event.proxy_mode)
        config.set('proxy_type', event.proxy_type)
        config.set('proxy_url', event.server_uri)
        config.set('proxy_port', event.server_port)
        if event.use_auth:
            config.set('proxy_user', event.username)
            config.set('proxy_password', event.proxy_password)
        else:
            config.set('proxy_user', None)
            config.set('proxy_password', None)

    def create_home_window(self):
        """Create a new HomeWindow instance and return it.

        The HomeWindow is the main Window in not connected mode. This method is
        used by the ``connect_and_register`` process as UI handler generator.
        The home window returned is an implementation of
        ``UIHandlerOfConnection``.

        Note that the window is created, but not displayed. It's up to the user
        to display it, by using one of the UI handler methods.
        """
        if self._home_window is not None:
            _logger.error(
                'Creation of a new HomeWindow(), but there is already one!\n'
                'This is not supposed to happen.')

        self._home_window = HomeWindow()

        # clean variable when destroyed.
        def _clean_home_window(_evt):
            self._home_window = None
        self.Bind(wx.EVT_WINDOW_DESTROY, _clean_home_window,
                  source=self._home_window)

        return self._home_window

    def OnInit(self):

        if not self._ensures_single_instance_running():
            return False

        self._task_bar_icon = TaskBarIcon()
        self._notifier = MessageNotifier(self._task_bar_icon)

        self.Bind(TaskBarIcon.EVT_OPEN_WINDOW, self._show_home_window)
        self.Bind(TaskBarIcon.EVT_EXIT, self._exit)
        return True

    def _show_home_window(self, event):
        if not self._session:
            if self._home_window:
                self._home_window.Show()
                self._home_window.Raise()
        else:
            if not self._main_window:
                self._main_window = MainWindow()
            self._main_window.Show()

    def _exit(self, _event):
        """Close all resources and quit the app."""
        _logger.debug('Exiting ...')
        if self._home_window:
            self._home_window.Destroy()
        self._task_bar_icon.Destroy()
        self._dummy_frame.Destroy()
        if self._container_list:
            self._container_list.stop()

    # Note (Kevin): OnEventLoopEnter(), from wx.App, is inconsistent. run()
    # is used instead.
    # See https://groups.google.com/forum/#!topic/wxpython-users/GArZiXVZrrA
    def run(self):
        """Start the event loop, and the connection process."""
        _logger.debug('run BajooApp')

        def _on_unhandled_exception(_exception):
            _logger.critical('Uncaught exception on Run process',
                             exc_info=True)

        future = connect_or_register(self.create_home_window)
        future.then(self._on_connection)
        future.then(None, _on_unhandled_exception)

        _logger.debug('Start main loop')
        self.MainLoop()

    @ensure_gui_thread
    def _on_connection(self, session):
        self._session = session
        self._home_window.Destroy()

        _logger.debug('Start DynamicContainerList() ...')
        self._container_list = DynamicContainerList(
            session, self._notifier.send_message,
            self._container_sync_pool.add,
            self._container_sync_pool.remove)
