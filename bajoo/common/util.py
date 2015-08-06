# -*- coding: utf-8 -*-
from .i18n import N_

# All currently known units:
# bytes, kilobytes, megabytes, gigabytes, terabytes
# petabytes, exabytes, zettabytes, yottabytes
_bytes_units = [N_('B'), N_('KB'), N_('MB'), N_('GB'), N_('TB'),
                N_('PB'), N_('EB'), N_('ZB'), N_('YB')]


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
            return "%.2f %s" % (value, unit)
        value /= 1024.0

    # The biggest unit reached: cannot translate anymore
    return "%.2f%s" % (value, _bytes_units[-1])


def open_folder(folder_path):
    """Open a folder using the platform-specific explorer."""

    import sys
    import os
    import subprocess

    if sys.platform.startswith('darwin'):
        subprocess.call(('open', folder_path))
    elif os.name == 'nt':
        os.startfile(folder_path)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', folder_path))


def main():
    values = [35, 145, 3245, 5434687, 4687465435, 53468768468576]
    print([human_readable_bytes(value) for value in values])


if __name__ == '__main__':
    main()
