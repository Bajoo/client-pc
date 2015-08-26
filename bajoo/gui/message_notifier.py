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

    def send_message(self, title, message):
        if sys.platform in ['win32', 'cygwin', 'win64']:
            self._tray_icon.ShowBalloon(title, message)
        else:
            if self._need_escape:
                message = escape(message)

            # TODO: set real icons
            icon_path = resource_filename('assets/icons/bajoo.ico')
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
