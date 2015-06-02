# -*- coding: utf-8 -*-

import wx


class BajooApp(wx.App):
    """Main class who start and manages the user interface.

    This is the first class created, just after the loading of configuration
    and the log initialization. It contains the global process of organization
    the different actions to perform and the user interface.

    All algorithms specific to this client (ie: not in the work layer) are cut
    into specific process functions. The BajooApp instance will call these
    functions and provides them appropriate user interface handlers. It will
    chain the different operations appropriately.

    The BajooApp will also manage the top-level windows life, and will catch
    the global user events (like quit).

    Call ``app.MainLoop()`` will start the event loop. The graphics elements
    will be displayed and the connexion process will start.
    """

    def __init__(self):
        # Don't redirect the stdout in a windows.
        wx.App.__init__(self, redirect=False)

    # TODO: Ensure there is only one instance of Bajoo started

    def OnInit(self):
        frame = wx.Frame(None, wx.ID_ANY, "Hello World")
        frame.Show(True)
        self.SetTopWindow(frame)

        # TODO: Create the TrayIcon

        # TODO: RefreshToken
        # ... TODO: then start sync.

        return True
