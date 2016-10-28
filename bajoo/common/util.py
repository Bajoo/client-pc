# -*- coding: utf-8 -*-

import os
import subprocess
import sys

from itertools import cycle

from .i18n import _, N_

# All currently known units:
# bytes, kilobytes, megabytes, gigabytes, terabytes
# petabytes, exabytes, zettabytes, yottabytes
_bytes_units = [N_('B'), N_('KB'), N_('MB'), N_('GB'), N_('TB'), N_('PB'),
                N_('EB'), N_('ZB'), N_('YB')]


def human_readable_bytes(value):
    """
    Translate a value in bytes to a human-readable string.

    Args:
        value: size in bytes

    Returns (str):
        translated string in current language
    """
    # Translate until the second-biggest unit
    for unit in _bytes_units[:-1]:
        if abs(value) < 1024.0:
            # if it does not reach kilobytes -> integer format
            str_format = "%d %s" if unit == _bytes_units[0] else "%.2f %s"
            return str_format % (value, _(unit))

        value /= 1024.0

    # The biggest unit reached: cannot translate anymore
    return "%.2f %s" % (value, _(_bytes_units[-1]))


def open_folder(folder_path):
    """Open a folder using the platform-specific explorer."""

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', folder_path))
    elif os.name == 'nt':
        os.startfile(folder_path)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', folder_path))


def xor(data, key):
    """Apply xor operation over data and key.

    The output value will have the same size as data. If key is shorter than
    data, then the key is repeated.

    Args:
        data (bytes/str/unicode): data to "encrypt".
        key (bytes/str/unicode): key used to apply xor.
    Returns:
        bytes: resulting binary data
    """
    if not isinstance(data, bytes):
        data = data.encode('utf-8')
    if not isinstance(key, bytes):
        key = key.encode('utf-8')

    data = list(bytearray(data))
    key = list(bytearray(key))
    return bytes(bytearray([c ^ k for c, k in zip(data, cycle(key))]))


def macos_activate_app():
    """
    This function allow to activate an app that is a background app.
    Because Bajoo has only a trayicon icon and no icon in the dock menu,
    osx consider it as a background app.  And so, the windows of a
    background may sometime appear behind other app's windows.

    Activate an app put its windows on the top of the other app's windows.
    """

    if not sys.platform == 'darwin':
        return

    subprocess.Popen(['osascript', '-e', '''\
        tell application "System Events"
          set procName to name of first process whose unix id is %s
        end tell
        tell application procName to activate
    ''' % os.getpid()])


def main():
    values = [35, 145, 3245, 5434687, 4687465435, 53468768468576]
    print([human_readable_bytes(value) for value in values])

    print('xor() of "foo bar" with key "baz":')
    print('\t%s' % repr(xor('foo bar', 'baz')))


if __name__ == '__main__':
    main()
