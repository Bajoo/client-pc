
from datetime import datetime
import glob
import locale
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import zipfile

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from ....__version__ import __version__
from ....api.session import Session
from ....common import path as bajoo_path
from ....common.i18n import _
from ....common.signal import Signal
from ....common.strings import err2unicode
from ....promise import reduce_coroutine
from ...event_promise import ensure_gui_thread

_logger = logging.getLogger(__name__)


class BugReportWindowController(object):
    """

    Attributes:
        destroyed (Signal): fired when the window is about to be destroyed.
    """
    def __init__(self, view_factory, app):
        self.view = view_factory(self)

        self.app = app
        self.destroyed = Signal()

    def show(self):
        self.view.show()

    def destroy(self):
        self.destroyed.fire()
        self.view.destroy()

    def notify_lang_change(self):
        self.view.notify_lang_change()

    def is_in_use(self):
        return self.view.is_in_use()

    def send_report_action(self, email, description):
        if not description:
            self.view.set_error(_('The bug description is required'))
            return

        if not email:
            self.view.set_error(_('The email field is required'))
            return

        if not re.match('.{2,}@.{2,}', email):
            self.view.set_error(_('The email must be valid.'))
            return

        self.view.disable_form()

        p = self._send_bug_report(email, description)

        p = p.then(self._display_confirm, self._display_error, exc_info=True)
        p.safeguard()

    def send_cancel_action(self):
        self.view.hide()

    @reduce_coroutine(safeguard=True)
    def _send_bug_report(self, email, description):
        _logger.debug("bug report creation")
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

                username = self._generate_report_file(zf, description, email)

            server_path = "/logs/%s/bugreport%s.zip" % \
                          (username,
                           datetime.now().strftime("%Y%m%d-%H%M%S"))

            if self.app.get_session():
                log_session = self.app.get_session()
            else:
                log_session = yield Session.from_client_credentials()

            with open(zip_path, 'rb') as file_content:
                yield log_session.upload_storage_file(
                    'PUT', server_path, file_content)
        finally:
            shutil.rmtree(tmpdir)

    def _generate_report_file(self, zip_object, message, reply_email):
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
        configfile.write("Reply email: %s\n" % reply_email)

        if self.app.user_profile is None:
            username = "Unknown_user"
            configfile.write("Connected: No\n")
        else:
            username = self.app.user_profile.email
            configfile.write("Connected: Yes\n")
            configfile.write(
                "User account: %s\n" % self.app.user_profile.email)
            configfile.write(
                "User root directory: %s\n" %
                self.app.user_profile._root_folder_path)

        locales = ", ".join(locale.getdefaultlocale())
        configfile.write("Default locales: %s\n" % locales)
        configfile.write("Message: \n\n%s" % message)

        zip_object.writestr("MESSAGE", configfile.getvalue().encode('utf-8'))
        configfile.close()

        return username

    @ensure_gui_thread()
    def _display_confirm(self, _):
        self.view.display_confirmation()

    @ensure_gui_thread()
    def _display_error(self, *exc_info):
        error = err2unicode(exc_info[0])

        if len(exc_info) is 3:
            _logger.error('Tentative to send bug report failed',
                          exc_info=exc_info)
        else:
            _logger.error('Tentative to send bug report failed: %s', error)

        self.view.enable_form()
        self.view.set_error(_('An error happened: %s') % error)
