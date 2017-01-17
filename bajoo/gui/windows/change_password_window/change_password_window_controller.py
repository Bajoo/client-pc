
import logging

from ....api import Session
from ....common.i18n import N_
from ....common.signal import Signal
from ....promise import reduce_coroutine
from ...event_promise import ensure_gui_thread
from ..base_window_controller import BaseWindowController

_logger = logging.getLogger(__name__)


class ChangePasswordWindowController(BaseWindowController):
    """Top-level Window used to change password.

    If an error occurs during the password change, an error message is
    displayed.
    If the operation succeed, the password_changed signal is raised, then the
    window closes itself.

    Attribute:
        password_changed (Signal): signal raised when the password has been
            successfully changed.
    """

    def __init__(self, view_factory, app, parent=None):
        BaseWindowController.__init__(self, view_factory, app, parent)

        self.password_changed = Signal()

    def show_modal(self):
        """Show the Windows and make it modal.

        Note: this method may block until the window is closed.
        """
        self.view.show_modal()

    @reduce_coroutine(safeguard=True)
    def change_password_action(self, old_password, new_password):
        """User has submit a password change

        Args:
            old_password (Text): actual password.
            new_password (Text): new password, replacing the actual one.
        """
        _logger.debug('Change user password ...')

        try:
            yield self.app._user.change_password(old_password, new_password)
        except:
            _logger.warning('Change password failed', exc_info=True)
            self._on_failure()
        else:
            new_session = yield Session.from_user_credentials(
                self.app._user.name, new_password)
            _logger.info('User password changed')
            self.app._session.update(new_session.access_token,
                                     new_session.refresh_token)
            self._on_success()

    def send_cancel_action(self):
        """The user abort the password change."""
        self.destroy()

    @ensure_gui_thread()
    def _on_success(self):
        self.password_changed.fire()
        self.destroy()

    @ensure_gui_thread()
    def _on_failure(self):
        self.view.show_error(
            N_('Failure when attempting to change password.'))
