# -*- coding: utf-8 -*-

import logging

import wx
from wx.lib.softwareupdate import SoftwareUpdate

from .common import config
from .common.path import get_data_dir
from .connection_registration_process import connect_or_register
from .container_sync_pool import ContainerSyncPool
from .dynamic_container_list import DynamicContainerList
from .gui.about_window import AboutBajooWindow
from .gui.event_future import ensure_gui_thread
from .gui.home_window import HomeWindow
from .gui.main_window import MainWindow
from .gui.message_notifier import MessageNotifier
from .gui.proxy_window import EVT_PROXY_FORM
from .gui.task_bar_icon import TaskBarIcon
from .gui.tab.creation_share_tab import CreationShareTab
from .gui.tab.list_shares_tab import ListSharesTab
from .gui.tab.general_settings_tab import GeneralSettingsTab
from .gui.tab.network_settings_tab import NetworkSettingsTab
from .gui.tab.advanced_settings_tab import AdvancedSettingsTab

from .common.i18n import N_


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
        self._about_window = None
        self._task_bar_icon = None
        self._notifier = None
        self._session = None
        self._container_list = None
        self._container_sync_pool = ContainerSyncPool(
            self._on_global_status_change, self._on_sync_error)

        if hasattr(wx, 'SetDefaultPyEncoding'):
            # wxPython classic only
            wx.SetDefaultPyEncoding("utf-8")

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

    @ensure_gui_thread
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
            return self._home_window

        return self.get_window('_home_window', HomeWindow)

    def get_window(self, attribute, cls):
        """Get a window, or create it if it's not instantiated yet.

        the attribute used to store the Window is set the None
        when the window is deleted.
        Args:
            attribute (str): attribute of this class, used to ref the window.
            cls (type): Class of the Window.
        Returns:
            Window
        """
        if getattr(self, attribute):
            return getattr(self, attribute)

        _logger.debug('Creation of Window %s' % attribute)
        window = cls()

        # clean variable when destroyed.
        def clean(_evt):
            setattr(self, attribute, None)

        self.Bind(wx.EVT_WINDOW_DESTROY, clean, source=window)

        setattr(self, attribute, window)
        return window

    def _notify_lang_change(self):
        """Notify a language change to all root translators instances"""
        for widget in (self._home_window, self._main_window,
                       self._about_window, self._task_bar_icon):
            if widget is not None:
                widget.notify_lang_change()

    def OnInit(self):

        if not self._ensures_single_instance_running():
            return False

        self._task_bar_icon = TaskBarIcon()
        self._notifier = MessageNotifier(self._task_bar_icon)

        self.Bind(TaskBarIcon.EVT_OPEN_WINDOW, self._show_window)
        self.Bind(TaskBarIcon.EVT_EXIT, self._exit)

        self.Bind(CreationShareTab.EVT_CREATE_SHARE_REQUEST,
                  self._on_request_create_share)
        self.Bind(ListSharesTab.EVT_DATA_REQUEST,
                  self._on_request_share_list)
        self.Bind(ListSharesTab.EVT_CONTAINER_DETAIL_REQUEST,
                  self._on_request_container_details)
        self.Bind(GeneralSettingsTab.EVT_CONFIG_REQUEST,
                  self._on_request_config)
        self.Bind(NetworkSettingsTab.EVT_CONFIG_REQUEST,
                  self._on_request_config)
        self.Bind(AdvancedSettingsTab.EVT_CONFIG_REQUEST,
                  self._on_request_config)

        return True

    def _show_window(self, event):
        """Catch event from tray icon, asking to show a window."""
        window = None

        if event.target == TaskBarIcon.OPEN_HOME:
            self._show_home_window()
        elif event.target == TaskBarIcon.OPEN_ABOUT:
            window = self.get_window('_about_window', AboutBajooWindow)
        elif event.target == TaskBarIcon.OPEN_SUSPEND:
            pass  # TODO: open window
        elif event.target == TaskBarIcon.OPEN_INVITATION:
            pass  # TODO: open window
        elif event.target == TaskBarIcon.OPEN_SETTINGS:
            window = self.get_window('_main_window', MainWindow)
            window.show_general_settings_tab()
        elif event.target == TaskBarIcon.OPEN_SHARES:
            window = self.get_window('_main_window', MainWindow)
            window.show_list_shares_tab()
        else:
            _logger.error('Unexpected "Open Window" event: %s' % event)

        if window:
            window.Show()
            window.Raise()

    def _show_home_window(self):
        if not self._session:
            if self._home_window:
                self._home_window.Show()
                self._home_window.Raise()
        else:
            if not self._main_window:
                self._main_window = MainWindow()
            self._main_window.Show()
            self._main_window.Raise()

    def _on_request_share_list(self, _event):
        if self._main_window:
            self._main_window.load_shares(
                self._container_list.get_list())

    def _on_request_container_details(self, event):
        l_container = event.container

        # TODO: Replace stimulated data
        l_container.encrypted = True
        l_container.stats = {
            'folders': 4,
            'files': 168,
            'space': 260000000
        }

        def _on_members_listed(members):
            l_container.container.members = members

            if self._main_window:
                self._main_window.set_share_details(l_container)

        if l_container.container:
            l_container.container.list_members() \
                .then(_on_members_listed)
        else:
            if self._main_window:
                self._main_window.set_share_details(l_container)

    def _on_request_config(self, _event):
        if self._main_window:
            self._main_window.load_config(config)

    def _on_request_create_share(self, event):
        share_name = event.share_name
        members = event.members

        from .api import TeamShare
        from .common.future import wait_all

        def on_members_added(__):
            if self._main_window:
                self._main_window.on_new_share_created(None)

        def on_share_created(share):
            futures = []

            self._notifier.send_message(
                N_('New team share created'),
                N_('The new team share %s has been successfully created')
                % share.name)

            for member in members:
                permissions = members[member]
                permissions.pop('user')
                futures.append(share.add_member(member, permissions))

            return wait_all(futures).then(on_members_added)

        TeamShare.create(self._session, share_name) \
            .then(on_share_created)

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
        if self._home_window:
            self._home_window.Destroy()
        _logger.debug('Start DynamicContainerList() ...')
        self._container_list = DynamicContainerList(
            session, self._notifier.send_message,
            self._container_sync_pool.add,
            self._container_sync_pool.remove)
        self._task_bar_icon.set_state(TaskBarIcon.SYNC_PROGRESS)

    @ensure_gui_thread
    def _on_global_status_change(self, status):
        """The global status of container sync pool has changed.

        We update the tray icon.
        """
        mapping = {
            ContainerSyncPool.STATUS_PAUSE: TaskBarIcon.SYNC_PAUSE,
            ContainerSyncPool.STATUS_SYNCING: TaskBarIcon.SYNC_PROGRESS,
            ContainerSyncPool.STATUS_UP_TO_DATE: TaskBarIcon.SYNC_DONE
        }
        if self._task_bar_icon:
            self._task_bar_icon.set_state(mapping[status])

    def _on_sync_error(self, err):
        self._notifier.send_message('Sync error', err)
