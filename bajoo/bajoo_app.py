# -*- coding: utf-8 -*-


import glob
import locale
import logging
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import wx
from wx.lib.softwareupdate import SoftwareUpdate

from . import __version__
from . import promise
from .api import Container, Session, TeamShare
from .common import autorun, config
from .common import path as bajoo_path
from .common.i18n import N_, _, set_lang
from .connection_registration_process import connect_or_register
from .container_model import ContainerModel
from .container_sync_pool import ContainerSyncPool
from .dynamic_container_list import DynamicContainerList
from .filesync import task_consumer
from .gui.about_window import AboutBajooWindow
from .gui.bug_report import BugReportWindow, EVT_BUG_REPORT
from .gui.change_password_window import ChangePasswordWindow
from .gui.common.language_box import LanguageBox
from .gui.event_promise import ensure_gui_thread
from .gui.form.members_share_form import MembersShareForm
from .gui.home_window import HomeWindow
from .gui.main_window import MainWindow
from .gui.message_notifier import MessageNotifier
from .gui.passphrase_window import PassphraseWindow
from .gui.proxy_window import EVT_PROXY_FORM
from .gui.tab import SettingsTab
from .gui.tab.account_tab import AccountTab
from .gui.tab.advanced_settings_tab import AdvancedSettingsTab  # REMOVE
from .gui.tab.creation_share_tab import CreationShareTab
from .gui.tab.details_share_tab import DetailsShareTab
from .gui.tab.list_shares_tab import ListSharesTab
from .gui.task_bar_icon import TaskBarIcon
from .local_container import LocalContainer
from .passphrase_manager import PassphraseManager
from .promise import Promise


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
        _user (User): When we are connected, _user is guaranted to exists and
            to be fully loaded (ie: with _user.name defined)
        profile (UserProfile)
    """

    def __init__(self):
        self._checker = None
        self._home_window = None
        self._main_window = None
        self._about_window = None
        self._contact_dev_window = None
        self._task_bar_icon = None
        self._notifier = None
        self._session = None
        self._user = None
        self._container_list = None
        self._container_sync_pool = ContainerSyncPool(
            self._on_global_status_change, self._on_sync_error)
        self._passphrase_manager = None

        self.user_profile = None

        if hasattr(wx, 'SetDefaultPyEncoding'):
            # wxPython classic only
            # wx.SetDefaultPyEncoding("utf-8")
            pass

        # Don't redirect the stdout in a windows.
        wx.App.__init__(self, redirect=False)

        self.SetAppName("Bajoo")

        # TODO: Set real value for production.
        base_url = "http://192.168.1.120:8000"
        self.InitUpdates(base_url, base_url + "/" + 'ChangeLog.txt')

        if config.get('auto_update'):
            self.AutoCheckForUpdate(0)

        # Note: the loop event only works if at least one wx.Window exists. As
        # wx.TaskBarIcon is not a wx.Window, we need to keep this unused frame.
        self._dummy_frame = wx.Frame(None)

        self.Bind(EVT_PROXY_FORM, self._on_proxy_config_changes)

        # Apply autorun on app startup to match with the config value
        autorun.set_autorun(config.get('autorun'))

        task_consumer.start()

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
                       self._about_window, self._task_bar_icon,
                       self._contact_dev_window):
            if widget:
                widget.notify_lang_change()

    def OnInit(self):

        if not self._ensures_single_instance_running():
            return False

        self._task_bar_icon = TaskBarIcon()
        self._notifier = MessageNotifier(self._task_bar_icon)

        self.Bind(TaskBarIcon.EVT_OPEN_WINDOW, self._show_window)
        self.Bind(TaskBarIcon.EVT_EXIT, self._exit)
        self.Bind(LanguageBox.EVT_LANG, self._on_lang_changed)
        self.Bind(TaskBarIcon.EVT_CONTAINER_STATUS_REQUEST,
                  self._container_status_request)

        self.Bind(CreationShareTab.EVT_CREATE_SHARE_REQUEST,
                  self._on_request_create_share)
        self.Bind(ListSharesTab.EVT_DATA_REQUEST,
                  self._on_request_share_list)
        self.Bind(ListSharesTab.EVT_CONTAINER_DETAIL_REQUEST,
                  self._on_request_container_details)
        self.Bind(SettingsTab.EVT_CONFIG_REQUEST, self._on_request_config)
        self.Bind(AdvancedSettingsTab.EVT_CHECK_UPDATES_REQUEST,
                  self._on_request_check_updates)
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
        self.Bind(ChangePasswordWindow.EVT_CHANGE_PASSWORD_SUBMIT,
                  self._on_request_change_password)
        self.Bind(AccountTab.EVT_DISCONNECT_REQUEST, self.disconnect)
        self.Bind(EVT_BUG_REPORT, self.send_bug_report)

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
            window.show_settings_tab()
        elif event.target == TaskBarIcon.OPEN_SHARES:
            window = self.get_window('_main_window', MainWindow)
            window.show_list_shares_tab()
        elif event.target == TaskBarIcon.OPEN_DEV_CONTACT:
            window = self.get_window('_contact_dev_window', BugReportWindow)
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

    def _container_status_request(self, _event):

        if not self._container_list:
            _logger.warning('the TaskBarIcon need the container list, '
                            'but the dynamic list is None')
            return

        mapping = {
            LocalContainer.STATUS_ERROR: TaskBarIcon.SYNC_ERROR,
            LocalContainer.STATUS_PAUSED: TaskBarIcon.SYNC_PAUSE,
            LocalContainer.STATUS_QUOTA_EXCEEDED: TaskBarIcon.SYNC_ERROR,
            LocalContainer.STATUS_WAIT_PASSPHRASE: TaskBarIcon.SYNC_ERROR,
            LocalContainer.STATUS_STOPPED: TaskBarIcon.SYNC_STOP,
            LocalContainer.STATUS_UNKNOWN: TaskBarIcon.SYNC_PROGRESS
        }
        containers_status = []
        for container in self._container_list.get_list():
            if container.status == LocalContainer.STATUS_STARTED:
                if container.is_up_to_date():
                    status = TaskBarIcon.SYNC_DONE
                else:
                    status = TaskBarIcon.SYNC_PROGRESS
            else:
                status = mapping[container.status]
            row = (container.model.name, container.model.path, status)
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

    def _on_request_check_updates(self, _event):
        _logger.debug("Check for updates...")
        self.CheckForUpdate()

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
                    % {"email": email, "name": share.model.name})
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
                    % {"email": email, "name": share.model.name})
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
            if container.model.id == share.id:
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
            shutil.copytree(container.model.path, new_path)
            shutil.rmtree(container.model.path)

            container.model.path = new_path
        except (IOError, OSError):
            _logger.critical(
                'Cannot move folder from %s to %s' % (
                    container.model.path, new_path),
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
            container, N_('The synchronization of this share is restarted.'))

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
                % share.model.name,
                is_error=True
            )
            if self._main_window:
                self._main_window.on_quit_or_delete_share(None)
            return

        yield self._container_list.refresh()

        self._notifier.send_message(
            _('Quit team share'),
            _('You have no longer access to team share %s.'
              % share.model.name))

        if self._main_window:
            self._main_window.load_shares(
                self._container_list.get_list(),
                _('You have no longer access to team share %s.'
                  % share.model.name))
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
            self._container_list.remove_container(share.model.id)
            yield share.container.delete()
            success_msg = _('A team share has been successfully deleted '
                            'from server.')
        except:
            _logger.exception('Unable to delete teamshare %s' %
                              share.model.name)
            error_msg = _('Team share %s cannot be '
                          'deleted from server.') % share.model.name

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

    @promise.reduce_coroutine(safeguard=True)
    def _on_request_change_password(self, event):
        _logger.debug('Change password request received %s:', event.data)

        old_password = event.data[u'old_password']
        new_password = event.data[u'new_password']

        try:
            yield self._user.change_password(old_password, new_password)
        except:
            _logger.warning('Change password failed', exc_info=True)
            if self._main_window:
                self._main_window.on_password_change_error(
                    N_('Failure when attempting to change password.'))
        else:
            new_session = yield Session.from_user_credentials(self._user.name,
                                                              new_password)
            self._session.access_token = new_session.access_token
            self._session.refresh_token = new_session.refresh_token
            self.user_profile.refresh_token = new_session.refresh_token

            if self._main_window:
                self._main_window.on_password_changed()

    def _exit(self, _event):
        """Close all resources and quit the app."""
        _logger.debug('Exiting ...')

        if self._home_window:
            self._home_window.Destroy()

        if self._main_window:
            self._main_window.Destroy()

        if self._about_window:
            self._about_window.Destroy()

        if self._contact_dev_window:
            self._contact_dev_window.Destroy()

        self._task_bar_icon.Destroy()

        if self._container_list:
            self._container_list.stop()

        self._container_sync_pool.stop()

        task_consumer.stop()

        self._dummy_frame.Destroy()
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

        future = connect_or_register(self.create_home_window)
        future.then(self._on_connection)
        future.then(None, _on_unhandled_exception)

        _logger.debug('Start main loop')
        self.MainLoop()

    @ensure_gui_thread
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
        self._task_bar_icon.set_state(TaskBarIcon.SYNC_PROGRESS)

    @ensure_gui_thread
    def _on_global_status_change(self, status):
        """The global status of container sync pool has changed.

        We update the tray icon.
        """
        if not self._user:
            return  # We are in a disconnection phase.

        mapping = {
            ContainerSyncPool.STATUS_PAUSE: TaskBarIcon.SYNC_PAUSE,
            ContainerSyncPool.STATUS_SYNCING: TaskBarIcon.SYNC_PROGRESS,
            ContainerSyncPool.STATUS_UP_TO_DATE: TaskBarIcon.SYNC_DONE
        }
        if self._task_bar_icon:
            self._task_bar_icon.set_state(mapping[status])

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
        self._task_bar_icon.set_state(TaskBarIcon.NOT_CONNECTED)
        if self._passphrase_manager:
            self._passphrase_manager.remove_passphrase()

        self._container_sync_pool.stop()
        self._container_sync_pool = ContainerSyncPool(
            self._on_global_status_change, self._on_sync_error)
        self._container_list.stop()
        self._container_list = None

        yield self._session.revoke()
        self._session = None

        _logger.debug('Now restart the connection process...')
        session_and_user = yield connect_or_register(self.create_home_window)
        yield self._on_connection(session_and_user)

    @promise.reduce_coroutine(safeguard=True)
    def send_bug_report(self, _evt):
        _logger.debug("bug repport creation")
        tmpdir = tempfile.mkdtemp()

        # identify where are last log files
        glob_path = os.path.join(bajoo_path.get_log_dir(), '*.log')
        newest = sorted(glob.iglob(glob_path),
                        key=os.path.getmtime,
                        reverse=True)

        zip_path = os.path.join(tmpdir, "report.zip")

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # grab the 5 last log files if exist
                for index in range(0, min(5, len(newest))):
                    zf.write(newest[index], os.path.basename(newest[index]))

                # collect config file
                config_path = os.path.join(bajoo_path.get_config_dir(),
                                           'bajoo.ini')
                try:
                    zf.write(config_path, 'bajoo.ini')
                except (IOError, OSError):
                    pass

                username = self._generate_report_file(zf, _evt.report)

            server_path = "/logs/%s/bugreport%s.zip" % \
                (username,
                 datetime.now().strftime("%Y%m%d-%H%M%S"))

            if self._session:
                log_session = self._session
            else:
                log_session = yield Session.from_client_credentials()

            with open(zip_path, 'rb') as file_content:
                yield log_session.upload_storage_file(
                    'PUT', server_path, file_content)

        finally:
            shutil.rmtree(tmpdir)

    def _generate_report_file(self, zip_object, message):
        configfile = StringIO()
        configfile.write("## Bajoo bug report ##\n\n")
        configfile.write("Creation date: %s\n" % str(datetime.now()))
        configfile.write("Bajoo version: %s\n" % __version__)
        configfile.write("Python version: %s\n" % sys.version)
        configfile.write("OS type: %s\n" % os.name)
        configfile.write("Platform type: %s\n" % sys.platform)
        configfile.write(
            "Platform details: %s\n" % platform.platform())
        configfile.write(
            "System default encoding: %s\n" % sys.getdefaultencoding())
        configfile.write(
            "Filesystem encoding: %s\n" % sys.getfilesystemencoding())

        if self.user_profile is None:
            username = "Unknown_user"
            configfile.write("Connected: No\n")
        else:
            username = self.user_profile.email
            configfile.write("Connected: Yes\n")
            configfile.write(
                "User account: %s\n" % self.user_profile.email)
            configfile.write(
                "User root directory: %s\n" %
                self.user_profile._root_folder_path)

        locales = ", ".join(locale.getdefaultlocale())
        configfile.write("Default locales: %s\n" % locales)
        configfile.write("Message: \n\n%s" % message)

        zip_object.writestr("MESSAGE", configfile.getvalue())
        configfile.close()

        return username
