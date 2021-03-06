# -*- coding: utf-8 -*-

import logging
import shutil
import sys

import wx

from . import encryption
from . import gtk_process
from . import promise
from .__version__ import __version__
from .api import Container, Session, TeamShare
from .app_status import AppStatus
from .common import autorun, config
from .common import path as bajoo_path
from .common.i18n import N_, _, set_lang
from .common.util import macos_activate_app
from .connection_registration_process import connect_or_register
from .container_model import ContainerModel
from .container_sync_pool import ContainerSyncPool
from .dynamic_container_list import DynamicContainerList
from .filesync import task_consumer
from .gui import AboutWindow, TaskBarIcon
from .gui.windows import BugReportWindow
from .gui.common.language_box import LanguageBox
from .gui.enums import WindowDestination
from .gui.event_promise import ensure_gui_thread
from .gui.form.members_share_form import MembersShareForm
from .gui.home_window import HomeWindow
from .gui.main_window import MainWindow
from .gui.message_notifier import MessageNotifier
from .gui.passphrase_window import PassphraseWindow
from .gui.proxy_window import EVT_PROXY_FORM
from .gui.tab import SettingsTab
from .gui.tab.account_tab import AccountTab
from .gui.tab.advanced_settings_tab import AdvancedSettingsTab
from .gui.tab.creation_share_tab import CreationShareTab
from .gui.tab.details_share_tab import DetailsShareTab
from .gui.tab.list_shares_tab import ListSharesTab
from .network import set_proxy
from .network.errors import NetworkError
from .passphrase_manager import PassphraseManager
from .promise import Promise
from .software_updater import SoftwareUpdater


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

    Attributes:
        _checker (wx.SingleInstanceChecker): Mutex used to avoid starting bajoo
            twice at the same time.
        _home_window (HomeWindow): if exists, the main window in not connected
            mode. This attribute is used to gives it the focus when the user
            interacts with the tray icon.
        _user (User): When we are connected, _user is guaranted to exists and
            to be fully loaded (ie: with _user.name defined)
        profile (UserProfile)
    """

    def __init__(self):
        self._checker = None
        if sys.platform == 'darwin':
            update_url = "https://www.bajoo.fr/downloads/osx/updates"
        else:
            update_url = "https://www.bajoo.fr/downloads/win32/updates"
        self._updater = SoftwareUpdater(self, update_url)
        self._home_window = None
        self._main_window = None
        self._about_window = None
        self._contact_dev_window = None
        self._task_bar_icon = None
        self._notifier = None
        self._session = None
        self._user = None
        self._container_list = None
        self.app_status = AppStatus(AppStatus.NOT_CONNECTED)
        self._container_sync_pool = ContainerSyncPool(
            self.app_status, self._on_sync_error)
        self._container_sync_pool.start()
        self._passphrase_manager = None
        self._exit_flag = False  # When True, the app is exiting.

        self.user_profile = None

        if hasattr(wx, 'SetDefaultPyEncoding'):
            # wxPython classic only
            # wx.SetDefaultPyEncoding("utf-8")
            pass

        # Don't redirect the stdout in a windows.
        wx.App.__init__(self, redirect=False)

        self.SetAppName("Bajoo")

        if config.get('auto_update'):
            self._updater.start()

        # Note: the loop event only works if at least one wx.Window exists. As
        # wx.TaskBarIcon is not a wx.Window, we need to keep this unused frame.
        self._dummy_frame = wx.Frame(None)

        self.Bind(EVT_PROXY_FORM, self._on_proxy_config_changes)
        self.app_status.changed.connect(self._on_app_status_changes)

        # Apply autorun on app startup to match with the config value
        autorun.set_autorun(config.get('autorun'))

        task_consumer.start()

    @property
    def version(self):
        """getter of application version"""
        return __version__

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
        self._checker = wx.SingleInstanceChecker(
            app_name,
            path=bajoo_path.get_data_dir())
        if self._checker.IsAnotherRunning():
            _logger.info('Prevents the user to start a second Bajoo instance.')

            wx.MessageBox(_("Another instance of Bajoo is actually running.\n"
                            "You can't open Bajoo twice."),
                          caption=_("Bajoo already started"))
            return False
        return True

    def _on_proxy_config_changes(self, event):
        config.set('proxy_mode', event.proxy_mode)
        config.set('proxy_type', event.proxy_type)
        config.set('proxy_url', event.server_uri)
        config.set('proxy_port', event.server_port)
        if event.use_auth:
            config.set('proxy_user', event.username)
            config.set('proxy_password', event.password)
        else:
            config.set('proxy_user', None)
            config.set('proxy_password', None)

        settings = {
            'type': event.proxy_type,
            'url': event.proxy_url,
            'port': event.proxy_port,
            'user': event.username if event.use_auth else None,
            'password': event.password if event.use_auth else None
        }
        set_proxy(event.proxy_mode, settings)

    @ensure_gui_thread(safeguard=True)
    def _on_app_status_changes(self, value):
        if self._task_bar_icon:
            self._task_bar_icon.set_app_status(value)
            # The task bar icon has no way to detect a container status change.
            # AppStatus is updated each time there a container status changes,
            # so we update the task bar icon's container list at the same time.
            self._container_status_request()

    @ensure_gui_thread()
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

        def window_ctor():
            return HomeWindow(self._notifier.send_message)
        return self.get_window('_home_window', window_ctor)

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

        _logger.debug('Creation of (wx) Window %s' % attribute)
        window = cls()

        # clean variable when destroyed.
        def clean(evt):
            setattr(self, attribute, None)
            evt.Skip()

        self.Bind(wx.EVT_WINDOW_DESTROY, clean, source=window)

        setattr(self, attribute, window)
        return window

    def _get_mvc_window(self, attribute, cls):
        """Get a window, or create it if it's not instantiated yet.

        the attribute used to store the Window is set to None
        when the window is deleted.
        Args:
            attribute (str): attribute of this class, used to ref the window.
            cls (Type[T]): Class of the Window.
        Returns:
            T: window
        """
        if getattr(self, attribute):
            return getattr(self, attribute)

        _logger.debug('Creation of (MVC) Window %s' % attribute)
        window = cls(self)

        window.destroyed.connect(lambda: setattr(self, attribute, None))
        setattr(self, attribute, window)
        return window

    def _notify_lang_change(self):
        """Notify a language change to all root translators instances"""
        for widget in (self._home_window, self._main_window,
                       self._about_window, self._task_bar_icon,
                       self._contact_dev_window):
            if widget:
                widget.notify_lang_change()

    def OnInit(self):
        try:
            if not self._ensures_single_instance_running():
                return False

            self._task_bar_icon = TaskBarIcon()

            self._notifier = MessageNotifier(self._task_bar_icon.view)

            self._task_bar_icon.navigate.connect(self._show_window)
            self._task_bar_icon.exit_app.connect(self._exit)

            self.Bind(LanguageBox.EVT_LANG, self._on_lang_changed)

            self.Bind(HomeWindow.EVT_RESEND_CONFIRM_EMAIL,
                      self._resend_confirm_email)
            self.Bind(CreationShareTab.EVT_CREATE_SHARE_REQUEST,
                      self._on_request_create_share)
            self.Bind(ListSharesTab.EVT_DATA_REQUEST,
                      self._on_request_share_list)
            self.Bind(ListSharesTab.EVT_CONTAINER_DETAIL_REQUEST,
                      self._on_request_container_details)
            self.Bind(SettingsTab.EVT_CONFIG_REQUEST, self._on_request_config)
            self.Bind(AdvancedSettingsTab.EVT_GET_UPDATER_REQUEST,
                      self._on_request_get_updater)
            self.Bind(AdvancedSettingsTab.EVT_RESTART_REQUEST,
                      self._restart_for_update)
            self.Bind(MembersShareForm.EVT_SUBMIT,
                      self._on_add_share_member)
            self.Bind(MembersShareForm.EVT_REMOVE_MEMBER,
                      self._on_remove_share_member)
            self.Bind(DetailsShareTab.EVT_QUIT_SHARE_REQUEST,
                      self._on_request_quit_share)
            self.Bind(DetailsShareTab.EVT_DELETE_SHARE_REQUEST,
                      self._on_request_delete_share)
            self.Bind(DetailsShareTab.EVT_START_SYNC_CONTAINER_REQUEST,
                      self._start_sync_container)
            self.Bind(DetailsShareTab.EVT_STOP_SYNC_CONTAINER_REQUEST,
                      self._stop_sync_container)
            self.Bind(DetailsShareTab.EVT_MOVE_CONTAINER_REQUEST,
                      self._move_synced_container)
            self.Bind(AccountTab.EVT_DATA_REQUEST,
                      self._on_request_account_info)
            self.Bind(AccountTab.EVT_DISCONNECT_REQUEST, self.disconnect)
        except:
            # wxPython hides OnInit's exceptions without any message.
            # Bug always reproducible on Linux with wxPython Gtk2 (classic)
            _logger.exception('Exception during BajooApp initialization')
            raise

        return True

    @ensure_gui_thread(safeguard=True)
    def _show_window(self, destination):
        """Catch event from tray icon, asking to show a window."""
        window = None

        if destination == WindowDestination.HOME:
            self._show_home_window()
        elif destination == WindowDestination.ABOUT:
            window = self._get_mvc_window('_about_window', AboutWindow)
        elif destination == WindowDestination.SUSPEND:
            pass  # TODO: open window
        elif destination == WindowDestination.INVITATION:
            pass  # TODO: open window
        elif destination == WindowDestination.SETTINGS:
            window = self.get_window('_main_window', MainWindow)
            window.show_settings_tab()
        elif destination == WindowDestination.SHARES:
            window = self.get_window('_main_window', MainWindow)
            window.show_list_shares_tab()
        elif destination == WindowDestination.DEV_CONTACT:
            window = self._get_mvc_window('_contact_dev_window',
                                          BugReportWindow)
        else:
            _logger.error('Unexpected "Navigation" destination: %s' %
                          destination)

        if window:
            try:
                window.show()
            except AttributeError:  # compatibility code for legacy wx GUI
                window.Show()
                window.Raise()
            macos_activate_app()

    def _show_home_window(self):
        if not self._session:
            if self._home_window:
                self._home_window.Show()
                self._home_window.Raise()
                macos_activate_app()
        else:
            if not self._main_window:
                self._main_window = MainWindow()
            self._main_window.Show()
            self._main_window.Raise()
            macos_activate_app()

    @promise.reduce_coroutine(safeguard=True)
    def _resend_confirm_email(self, event):
        session = yield Session.from_client_credentials()
        yield session.send_api_request(
            'POST', '/user/%s/resend_activation_email' % event.user_email)

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_share_list(self, _event):
        """
        Handle the request `get share list`: refresh the dynamic container
        list in bajoo_app and give it to the share list tab in main_window.
        """

        yield self._container_list.refresh()

        futures = []
        for container in self._container_list.get_list():
            if isinstance(container.container, TeamShare):
                futures.append(container.container.list_members())

        error_msg = None
        try:
            yield Promise.all(futures)
        except Exception as error:
            _logger.exception('Actualize member list of shares has failed.')
            error_msg = _('Error occurred: %s.') % error

        if self._main_window:
            self._main_window.load_shares(self._container_list.get_list(),
                                          error_msg=error_msg, show_tab=False)

    def _container_status_request(self):
        """Update the task bar icon."""

        if not self._container_list:
            _logger.warning('the TaskBarIcon need the container list, '
                            'but the dynamic list is None')
            return

        containers_status = []
        for container in self._container_list.get_list():
            row = (container.name, container.path, container.status)
            containers_status.append(row)

        self._task_bar_icon.set_container_status_list(containers_status)

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_container_details(self, event):
        """
        Handle the request `get container detail`: fetch the team share's
        members if necessary, then give all info of the LocalContainer
        & Container object to the share detail tab.

        Args:
            event.container (LocalContainer)
        """
        l_container = event.container

        # If this is a TeamShare, fetch its members.
        if isinstance(l_container.container, TeamShare):
            yield l_container.container.list_members()
        if self._main_window:
            self._main_window.set_share_details(l_container)

    def _on_request_config(self, _event):
        if self._main_window:
            self._main_window.load_config(config)

    def _on_request_get_updater(self, event):
        event.EventObject.set_updater(self._updater)

    @promise.reduce_coroutine(safeguard=True)
    def _on_add_share_member(self, event):
        """
        Handle the request `add/modify a new member of a share`.
        """
        share = event.share
        email = event.user_email
        permission = event.permission

        # Check event params
        if not share or not email or not permission:
            return

        if share.container:
            try:
                yield share.container.add_member(email, permission)
            except:
                _logger.exception('Adding a member has failed')

                if self._main_window:
                    self._main_window.on_share_member_added(
                        share, None, None,
                        N_('Cannot add this member to team share; '
                           'maybe this account does not exist.'))
                return

            # Refresh the member list
            yield share.container.list_members()

            if self._main_window:
                self._main_window.on_share_member_added(
                    share, email, permission,
                    N_("%(email)s has been given access to team "
                       "share \'%(name)s\'")
                    % {"email": email, "name": share.name})
        else:
            if self._main_window:
                self._main_window.on_share_member_added(
                    share, None, None,
                    N_('Unidentified container, cannot add member'))

    @promise.reduce_coroutine(safeguard=True)
    def _on_remove_share_member(self, event):
        share = event.share
        email = event.email

        if share.container:
            try:
                yield share.container.remove_member(email)
            except:
                _logger.exception('Remove member of a share has failed.')
                if self._main_window:
                    self._main_window.on_share_member_removed(
                        share, None,
                        N_('Cannot remove this member from this team share.'))
                return

            yield share.container.list_members()
            if self._main_window:
                self._main_window.on_share_member_removed(
                    share, email,
                    N_('%(email)s\'s access to team share \'%(name)s\' '
                       'has been removed.')
                    % {"email": email, "name": share.name})
        else:
            if self._main_window:
                self._main_window.on_share_member_removed(
                    share, None,
                    N_('Unidentified container, cannot remove member'))

    def _on_lang_changed(self, event):
        """
        Handle the request of changing the application language.
        """
        config.set('lang', event.lang)
        set_lang(event.lang)

        gtk_process.remote_call('set_lang', 'bajoo.common.i18n', event.lang)

        self._notify_lang_change()

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_create_share(self, event):
        """
        Handle the request `create a new team share`. This function can
        send multiple API requests to create a new share and then add
        member(s) to it. Failure when adding a member does not effect
        other requests.
        """
        share_name = event.share_name
        encrypted = event.encrypted
        members = event.members
        do_not_sync = event.do_not_sync
        local_path = event.path

        # Create share
        try:
            share = yield TeamShare.create(self._session, share_name,
                                           encrypted)
        except:
            _logger.exception('Creation of a new TeamShare has failed.')
            if self._main_window:
                self._main_window.load_shares(
                    self._container_list.get_list(),
                    None, _('Cannot create share %s') % share_name)
            return

        # Add all members
        futures = []
        for member in members:
            permissions = members[member]
            permissions.pop('user')
            futures.append(share.add_member(member, permissions))

        error_msg = None
        try:
            yield Promise.all(futures)
        except:
            _logger.exception('Add of a TeamShare member has failed.')
            error_msg = N_('Some members cannot be added to this team share. '
                           'Please verify the email addresses.')
        success_msg = _('Team share %s has been successfully '
                        'created') % share_name

        share_model = ContainerModel(
            share.id, share.name, path=local_path,
            container_type='teamshare', do_not_sync=do_not_sync)

        self._container_list.add_container(share, share_model)

        yield self._container_list.refresh()

        for container in self._container_list.get_list():
            if container.id == share.id:
                yield container.container.list_members()
                break

        if self._main_window:
            self._main_window.load_shares(self._container_list.get_list(),
                                          success_msg, error_msg)

    def _move_synced_container(self, event):
        container = event.container
        new_path = event.path

        self._container_list.stop_sync_container(container)

        try:
            container.is_moving = True

            # Check if selected folder exists
            new_path = container.get_not_existing_folder(new_path)
            shutil.copytree(container.path, new_path)
            shutil.rmtree(container.path)

            container.model.path = new_path
        except (IOError, OSError):
            _logger.critical(
                'Cannot move folder from %s to %s' % (
                    container.path, new_path),
                exc_info=True)
        finally:
            container.is_moving = False
            self._container_list.start_sync_container(container)
            self._container_updated(
                container, N_('This folder has been succesfully moved'
                              ' to the new location.'))

    def _stop_sync_container(self, event):
        container = event.container
        self._container_list.stop_sync_container(container)
        self._container_updated(
            container, N_('The synchronization of this share is stopped.'))

    def _start_sync_container(self, event):
        container = event.container
        self._container_list.start_sync_container(container)
        self._container_updated(
            container, N_('The synchronization of this share has restarted.'))

    def _container_updated(
            self, container, success_msg=None, error_msg=None):
        if self._main_window:
            self._main_window.on_container_updated(
                container, success_msg, error_msg)

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_quit_share(self, event):
        share = event.share
        # TODO: stop the synchro on this share

        try:
            yield share.container.remove_member(self._user.name,
                                                is_self_quit=True)
        except:
            _logger.exception('Exception when quitting a share.')
            self._notifier.send_message(
                _('Error'),
                _('An error occured when trying to quit team share %s.')
                % share.name,
                is_error=True
            )
            if self._main_window:
                self._main_window.on_quit_or_delete_share(None)
            return

        yield self._container_list.refresh()

        self._notifier.send_message(
            _('Quit team share'),
            _('You have no longer access to team share %s.'
              % share.name))

        if self._main_window:
            self._main_window.load_shares(
                self._container_list.get_list(),
                _('You have no longer access to team share %s.'
                  % share.name))
            self._main_window.on_quit_or_delete_share(share)

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_delete_share(self, event):
        """
        Handle the request `delete a share`. Stop the local synchronization
        & send the API request.
        """
        share = event.share

        success_msg = None
        error_msg = None
        try:
            # TODO: should we also delete the folder ?
            self._container_list.remove_container(share.id)
            yield share.container.delete()
            success_msg = _('A team share has been successfully deleted '
                            'from server.')
        except:
            _logger.exception('Unable to delete teamshare %s' %
                              share.name)
            error_msg = _('Team share %s cannot be '
                          'deleted from server.') % share.name

        yield self._container_list.refresh()
        if self._main_window:
            self._main_window.load_shares(
                self._container_list.get_list(),
                success_msg, error_msg)

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_account_info(self, event):

        quota_info = yield self._user.get_quota()
        used_quota, allowed_quota = quota_info

        # user.name must be set.
        if self._main_window:
            self._main_window.set_account_info({
                'email': self._user.name,
                'account_type': _('Beta tester account'),
                # Note: In beta, there is only one account type.
                'is_best_account_type': True,
                'n_shares': len(self._container_list.get_list()),
                'quota': allowed_quota,  # 2GB
                'quota_used': used_quota  # 500MB
            })

    @ensure_gui_thread(safeguard=True)
    def _exit(self):
        """Close all resources and quit the app."""
        if self._exit_flag:
            return
        self._exit_flag = True
        _logger.debug('Exiting ...')

        if self._home_window:
            self._home_window.Destroy()

        if self._main_window:
            self._main_window.Destroy()

        if self._about_window:
            self._about_window.destroy()

        if self._contact_dev_window:
            self._contact_dev_window.destroy()

        self._task_bar_icon.destroy()
        # TODO: this manual deletion is required because cross-process
        # references are not handled by the garbage collector.
        self._task_bar_icon.view = None
        self._task_bar_icon = None

        if self._container_list:
            self._container_list.stop()

        self._container_sync_pool.stop()

        # Encryption must be stopped before filesync. Otherwise, filesync will
        # wait the end of all encryption tasks before returning.
        encryption.stop()
        task_consumer.stop()

        self._dummy_frame.Destroy()

        # This wx App_CleanUp exit handler is bogged on macos and
        # results in a segmentation fault at each exit.
        # It probably tries to free a wxWidget that was already destroyed.
        # But which one... (it is not the dummy frame)
        if sys.platform == 'darwin' and sys.version_info[0] < 3:
            import atexit
            for handler in atexit._exithandlers:
                if handler[0].__name__ == 'App_CleanUp':
                    atexit._exithandlers.remove(handler)
                    break

        _logger.debug('Exiting done !')

    # Note (Kevin): OnEventLoopEnter(), from wx.App, is inconsistent. run()
    # is used instead.
    # See https://groups.google.com/forum/#!topic/wxpython-users/GArZiXVZrrA
    def run(self):
        """Start the event loop, and the connection process."""
        _logger.debug('run BajooApp')

        def _on_unhandled_exception(_exception):
            _logger.critical('Uncaught exception on Run process',
                             exc_info=True)

        p = connect_or_register(self.create_home_window)
        p = p.then(self._on_connection)
        p.then(None, _on_unhandled_exception)

        _logger.debug('Start main loop')
        self.MainLoop()

    @ensure_gui_thread()
    def _on_connection(self, session_and_user):
        self._session, self._user, self.user_profile = session_and_user

        def _on_refresh_token_changed(session):
            if self.user_profile:
                self.user_profile.refresh_token = session.refresh_token

        self._session.token_changed_callback = _on_refresh_token_changed

        if self._home_window:
            self._home_window.Destroy()
            self._home_window = None

        if not self._passphrase_manager:
            self._passphrase_manager = PassphraseManager(self.user_profile)
            self._passphrase_manager.set_user_input_callback(
                PassphraseWindow.ask_passphrase)
            cb = self._passphrase_manager.get_passphrase
            Container.passphrase_callback = staticmethod(cb)

        _logger.debug('Start DynamicContainerList() ...')
        self._container_list = DynamicContainerList(
            self._session, self.user_profile, self._notifier.send_message,
            self._container_sync_pool.add,
            self._container_sync_pool.remove)
        self.app_status.value = AppStatus.SYNC_IN_PROGRESS

    def _on_sync_error(self, err):
        self._notifier.send_message(_('Sync error'), _(err), is_error=True)

    @promise.reduce_coroutine(safeguard=True)
    def disconnect(self, _evt):
        """revoke token and return the the home window."""

        # TODO: erase profile file
        self.user_profile.refresh_token = None
        self.user_profile = None

        _logger.info('Disconnect user.')
        if self._home_window:
            self._home_window.Destroy()
            self._home_window = None
        if self._main_window:
            self._main_window.Destroy()
            self._main_window = None

        self._user = None
        if self._passphrase_manager:
            self._passphrase_manager.remove_passphrase()

        self._container_sync_pool.stop()

        self.app_status.value = AppStatus.NOT_CONNECTED
        self._container_sync_pool = ContainerSyncPool(
            self.app_status, self._on_sync_error)
        self._container_sync_pool.start()
        self._container_list.stop()
        self._container_list = None

        try:
            yield self._session.revoke()
        except NetworkError:
            _logger.warn('Token revocation failed', exc_info=True)
        self._session = None

        _logger.debug('Now restart the connection process...')
        session_and_user = yield connect_or_register(self.create_home_window)
        yield self._on_connection(session_and_user)

    def _restart_if_idle(self, evt):
        evt.Skip()
        if not evt.GetEventObject().IsTopLevel():
            return

        window_being_destroyed = None
        if evt.GetEventType() == wx.EVT_WINDOW_DESTROY.typeId:
            window_being_destroyed = evt.GetEventObject()
        self.restart_when_idle(_already_bound=True,
                               _window_being_destroyed=window_being_destroyed)

    @ensure_gui_thread(safeguard=True)
    def restart_when_idle(self, _already_bound=False,
                          _window_being_destroyed=None):
        # Under Windows, the window being destroyed during EVT_WINDOW_DESTROY
        # is still alive and visible. "_window_being_destroyed" contains this
        # window, so we can ignore it.
        if not _already_bound:
            _logger.info('Will restart Bajoo when all windows will be closed.')
        all_windows = (self._home_window, self._main_window,
                       self._about_window, self._contact_dev_window)

        def is_in_use(w):  # Compatibility code between Wx and MVC windows
            try:
                return w.is_in_use()
            except AttributeError:
                return w.IsShown()

        if any(w and w is not _window_being_destroyed and is_in_use(w)
               for w in all_windows):
            if not _already_bound:
                self.Bind(wx.EVT_SHOW, self._restart_if_idle)
                self.Bind(wx.EVT_WINDOW_DESTROY, self._restart_if_idle)
        else:
            self.Unbind(wx.EVT_SHOW, handler=self._restart_if_idle)
            self.Unbind(wx.EVT_WINDOW_DESTROY, handler=self._restart_if_idle)
            return self._restart_for_update()

    @ensure_gui_thread()
    def _restart_for_update(self, _evt=None):
        if self._exit_flag:
            return
        _logger.info('Restart Bajoo now.')
        self._updater.register_restart_on_exit()
        return self._exit()

    def get_session(self):
        return self._session
