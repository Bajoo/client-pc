
import re
import sys
from .about_window import AboutWindowTestController
from .task_bar_icon import TaskBarIconTestController


def wx_context():
    import wx
    app = wx.App()
    app.SetExitOnFrameDelete(False)

    yield app.ExitMainLoop

    # at least 1 frame is needed to run the loop.
    win = wx.Frame(None)  # noqa
    app.MainLoop()


def gtk_context():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk

    # workaround for https://bugzilla.gnome.org/show_bug.cgi?id=622084
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Force reload of all gui-related modules.
    # It'll detect the hidden GTK3 classes.
    pattern = re.compile('^bajoo.gui')
    for module in list(sys.modules):
        if pattern.match(module):
            del sys.modules[module]

    yield Gtk.main_quit

    Gtk.main()


context_by_name = {
    'wx': wx_context,
    'gtk': gtk_context,
    'appindicator': gtk_context
}


graphic_items = {
    'about_window': (AboutWindowTestController, 'windows.about_window', {
        'wx': 'AboutWindowWxView',
        'gtk': 'AboutWindowGtkView'
    }),
    'task_bar_icon': (TaskBarIconTestController, 'task_bar_icon', {
        'wx': 'TaskBarIconWxView',
        'gtk': 'TaskBarIconGtkView',
        'appindicator': 'TaskBarIconAppIndicatorView',
    })
}
