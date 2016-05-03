# -*- coding: utf-8 -*-

import atexit
import logging
import os
import sys
from .common.periodic_task import PeriodicTask

if hasattr(sys, 'frozen'):
    import esky
    import esky.util


_logger = logging.getLogger(__name__)


class NotFrozenException(Exception):
    """Raised when an operation requires Bajoo to be frozen, but it's not."""
    pass


class AbortException(Exception):
    """Special exception raised to interrupt an update.
    Internal use use.
    """
    pass


class SoftwareUpdater(object):
    """Detect new versions of Bajoo, and update the software.

    The updater can be started either in sync or async mode. In asynchronous
    mode, the last version available is checked once a day. If there is a new
    version, the program will silently update itself.
    After the download of updated files, BajooApp is informed that a restart is
    required. The restart is done as soon as BajooApp allow it.

    The progression status is kept.
    """

    def __init__(self, app, base_url):
        """

        Args:
            app (BajooApp): BajooApp. It's the app which can restart (or not)
                the executable when app.restart_when_idle() is called.
            base_url (str): URL of the "download" folder where the upgrades are
                stored.
        """
        self.app = app
        self._esky = None
        self._abort_flag = False
        self._periodic_task = PeriodicTask('App Updater', 3600 * 24,
                                           self._timer_thread)

        if hasattr(sys, 'frozen'):
            self._esky = esky.Esky(sys.executable, base_url)
            try:
                # Remove old files from previous versions.
                self._esky.cleanup()
            except:
                _logger.warn('Esky cleanup failed', exc_info=True)

    def start(self):
        if not self._esky:
            return
        self._periodic_task.start()

    def stop(self):
        self._abort_flag = True
        self._periodic_task.stop()

    def _timer_thread(self):
        """Check for update at regular interval."""

        try:
            self._background_check_update()
        except AbortException:
            _logger.debug('Update operation aborted.')
        except:
            _logger.warn('Check update failed', exc_info=True)

    def _background_check_update(self):
        if not self._esky:
            raise NotFrozenException()
        if self._abort_flag:
            raise AbortException()

        last_version = self._esky.find_update()
        if not last_version:
            return  # no update available

        self._esky.auto_update(self._update_progress)

        self.app.restart_when_idle(self)

    def register_restart_on_exit(self):
        """Register a restart at next exit.

        This method should be called just before restarting, by the BajooApp.
        """
        path_exe = esky.util.appexe_from_executable(sys.executable)

        def restart():
            os.chdir(os.path.dirname(path_exe))
            os.execv(path_exe, [path_exe] + sys.argv[1:])

        atexit.register(restart)

    def _update_progress(self, status):
        if self._abort_flag:
            raise AbortException()

        _logger.debug('update bajoo status: %s', status)
        # TODO: keep status to display it if needed.
        # 'status': 'searching'
        # 'status': 'found', 'new_version'
        # 'status': 'downloading', 'received': 123, 'size': 456 (size optional)
        # 'status': 'retrying', 'exception': Exception
        # 'status': 'error', 'exception': Exception
        # 'status': 'ready', 'path': '.../updates/ready/bajoo.0.999.win32'
        # 'status': 'installing', 'new_version': 3

        # 'status': 'cleaning up'
        # 'status': 'done'
