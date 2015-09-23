# -*- coding: utf-8 -*-

import logging
import os
import sys
if sys.platform not in ['win32', 'cygwin', 'win64']:
    import notify2
    try:
        from html import escape
    except:  # Python 2
        from cgi import escape

from ..common.path import resource_filename

_logger = logging.getLogger(__name__)


class MessageNotifier(object):
    """Notify messages to the user.

    Cross-platform way to send a text message to the user.

    Under Windows, the `ShowBalloon()` method of the trayIcon is used.
    Under Linux, the standard notification system is used.

    """

    def __init__(self, tray_icon):
        if sys.platform in ['win32', 'cygwin', 'win64']:
            self._tray_icon = tray_icon
        else:
            notify2.init('Bajoo')
            self._need_escape = 'body-markup' in notify2.get_server_caps()

    def send_message(self, title, message, is_error=False):
        """Display a notification.

        Args:
            title (str):
            message (str):
            is_error (boolean): Change the displayed icon, to indicate if
                it's an error message or an informative message.
        """
        if is_error:
            icon_path = resource_filename(
                'assets/images/icon_notification_error.png')
        else:
            icon_path = resource_filename(
                'assets/images/trayicon_status/sync.png')

        if sys.platform in ['win32', 'cygwin', 'win64']:
            # Before Windows 10, the balloon has no icon visible.
            # On Windows 10, the icon from the TrayIcon is used.
            # Unfortunately, no matter what is the size of the original icon,
            # the icon is resized to fit in the task bar (probably 32x32),
            # then resized again to display the notification. The result is
            # ugly, but wxPython offers no ways to fix it.
            # TODO: use an alternative notification method.
            self._tray_icon.ShowBalloon(title, message)
        else:
            if self._need_escape:
                message = escape(message)

            # notify2 need absolute path
            icon_path = os.path.abspath(icon_path)
            n = notify2.Notification(title, message, icon_path)

            import dbus
            try:
                n.show()
            except dbus.DBusException:
                _logger.warning('unexpected DBus error when trying to display '
                                'a notification', exc_info=True)
                raise


def main():
    notifier = MessageNotifier(None)
    notifier.send_message('Bajoo notification !',
                          'Hello, world !\nTEST ⓤⓝⓘⓒⓞⓓⓔ')


if __name__ == '__main__':
    main()
