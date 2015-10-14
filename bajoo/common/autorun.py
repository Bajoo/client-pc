# -*- coding: utf-8 -*-
import os
import sys

if sys.platform in ['win32', 'win64']:
    import win32com.client
    from win32com.shell import shell, shellcon


def _win_startup_directory():
    """
    Returns (str): the path to startup directory
        Tested on Windows 8:
        C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\
        \Programs\Startup
    """
    return shell.SHGetFolderPath(0, shellcon.CSIDL_ALTSTARTUP, 0, 0)


def _win_shortcut_path():
    """Get the path of the startup shortcut on Windows"""
    shortcut_name = 'Bajoo.lnk'
    return os.path.join(_win_startup_directory(), shortcut_name)


def is_autorun():
    """
    Check if autorun is enabled.
    Returns: (boolean)
    """
    if not can_autorun():
        return False

    if sys.platform in ['win32', 'win64']:
        return os.path.isfile(_win_shortcut_path())


def can_autorun():
    """
    Check if Bajoo supports autorun feature for current platform.
    (This function is going to be removed once Bajoo supports autorun
    for all platforms.)

    Returns: (boolean)
    """
    return sys.platform in ['win32', 'win64']


def _set_autorun_win(autorun=True):
    """
    Enable/Disable autorun on Windows.

    On Windows, the autorun is done by creating a shortcut to Bajoo.exe
    in user's Startup folder (not in the common Startup folder for All Users).
    """
    if autorun:
        if not is_autorun():
            # Create shortcut
            ws = win32com.client.Dispatch("wscript.shell")
            scut = ws.CreateShortcut(_win_shortcut_path())
            scut.TargetPath = sys.executable
            scut.Save()
    else:
        # Delete shortcut
        if os.path.isfile(_win_shortcut_path()):
            os.remove(_win_shortcut_path())


def set_autorun(autorun=True):
    """
    Enable/Disable the automatic launch of Bajoo at system startup.
    """
    if sys.platform in ['win32', 'win64']:
        return _set_autorun_win(autorun)

    return False
