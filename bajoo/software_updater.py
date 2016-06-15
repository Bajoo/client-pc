# -*- coding: utf-8 -*-

import atexit
import logging
import os
import sys
try:
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import HTTPError, URLError
import warnings
from .common.periodic_task import PeriodicTask
from .common.signal import Signal
from .common.strings import err2unicode, to_unicode

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

    Attributes:
        status (str): One of the following:
            - 'disabled': The app is not packaged with Esky.
            - 'aborted': Operation has been aborted.
            - 'idle': No ongoing operation.
            - 'searching'
            - 'found'; self.new_version is set.
            - 'downloading': The new version is downloading. self.received and
                optionally self.size are set.
            - 'retrying': retrying after an error. self.exception is set.
            - 'error': An error happened. self.exception is set.
            - 'ready': The update has been downloading, and will be installed.
            - 'installing'
            - 'cleaning up': remove old files.
            - 'done': Installation has been done. Bajoo should be restarted.
        dl_received (int): number of bytes received (during download phase)
        dl_total_size (int): size of the files to download (during the download
            phase)
        exception (Exception): if set, exception raised during failed update.
        new_version (str): most recent version available.

        status_changed (Signal): fired when the status changes.
            Handlers received theses arguments:
                status (str)
                dl_received (int, optional)
                dl_total_size (int, optional)
                exception (Exception, optional),
                new_version (str, optional)

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
                                           self._background_check_update)

        self.status_changed = Signal()
        self.status = 'idle'
        self.dl_received = None
        self.dl_total_size = None
        self.exception = None
        self.new_version = None

        if hasattr(sys, 'frozen'):
            exec_path = to_unicode(sys.executable,
                                   in_enc=sys.getfilesystemencoding())
            self._esky = esky.Esky(exec_path, base_url)
            try:
                # Remove old files from previous versions.

                with warnings.catch_warnings():
                    # cleanup can produces a lot of warnings about unicode
                    # badly handled. We don't need them.
                    self._esky.cleanup()
            except:
                _logger.warn('Esky cleanup failed', exc_info=True)
        else:
            self.status = 'disabled'

    def start(self):
        if not self._esky:
            return
        self._periodic_task.start()

    def stop(self):
        self._abort_flag = True
        self._periodic_task.stop()

    def check_update(self):
        """Start checking for update as soon as possible."""
        return self._periodic_task.apply_now()

    def _background_check_update(self, _periodic_task):
        if not self._esky:
            raise NotFrozenException()
        if self._abort_flag:
            raise AbortException()
        self.status = 'idle'
        self.status_changed.fire(self.status)

        try:
            last_version = self._esky.find_update()
        except (HTTPError, URLError) as e:
            _logger.warn('Update search failed: %s', err2unicode(e))
            self.status = 'error'
            self.exception = e
            self.status_changed.fire(self.status)
            return
        except Exception as e:
            self.status = 'error'
            self.exception = e
            self.status_changed.fire(self.status)
            raise

        if not last_version:
            return  # no update available

        try:
            self._esky.auto_update(self._update_progress)
        except AbortException:
            _logger.debug('Update operation aborted.')
            return
        except UnicodeError:
            # Esky can raise errors during the cleanup phase. In this case, we
            # can safely ignore the error.
            if self.status == 'done':
                _logger.warn('Unicode error in Esky update. This warning can '
                             'be safely ignored.', exc_info=True)
            else:
                raise
        self.app.restart_when_idle()

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
            self.status = 'aborted'
            self.status_changed.fire(status)
            raise AbortException()

        if status['status'] != 'downloading' or self.status != 'downloading':
            _logger.debug('update bajoo status: %s', status)
        self.status = status['status']
        self.dl_received = status.get('received')
        self.dl_total_size = status.get('size')
        self.exception = status.get('exception')
        if 'new_version' in status:
            self.new_version = status['new_version']
        if status['status'] == 'error':
            self.new_version = None

        self.status_changed.fire(self.status)
