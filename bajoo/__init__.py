# -*- coding: utf-8 -*-

from .__version__ import __version__  # noqa

import wx


def main():
    """Entry point of the Bajoo client."""
    app = wx.App()
    frame = wx.Frame(None, wx.ID_ANY, "Hello World")
    frame.Show(True)
    app.MainLoop()
    pass


if __name__ == "__main__":
    main()
