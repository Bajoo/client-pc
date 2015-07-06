# -*- coding: utf-8 -*-

import wx

from ..common.i18n import N_
from ..common.path import resource_filename
from .tab import ListSharesTab
from .tab import AccountTab
from .tab import GeneralSettingsTab
from .tab import NetworkSettingsTab
from .tab import AdvancedSettingsTab


class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None)
        self._view = MainWindowListbook(self)

        sizer = wx.BoxSizer()
        sizer.Add(self._view, 1, wx.EXPAND)

        self.SetSizer(sizer)


class MainWindowListbook(wx.Listbook):
    """
    The layout of the main window, which initiates & contains all tabs.
    """

    def __init__(self, parent):
        wx.Listbook.__init__(self, parent, style=wx.BK_LEFT)

        # TODO: Set proper image for each tab
        image_list = wx.ImageList(64, 64)
        image_list.Add(wx.Image(resource_filename(
            'assets/images/settings.png')).ConvertToBitmap())
        self.AssignImageList(image_list)

        self.AddPage(ListSharesTab(self),
                     N_("My Shares"), imageId=0)
        self.AddPage(AccountTab(self),
                     N_("My Account"), imageId=0)
        self.AddPage(GeneralSettingsTab(self),
                     N_("General Settings"), imageId=0)
        self.AddPage(NetworkSettingsTab(self),
                     N_("Network Settings"), imageId=0)
        self.AddPage(AdvancedSettingsTab(self),
                     N_("Advanced Settings"), imageId=0)

        self.Bind(wx.EVT_LISTBOOK_PAGE_CHANGED, self.on_page_changed)
        self.on_page_changed()

    def on_page_changed(self, _event=None):
        self.GetParent().SetTitle(self.GetPageText(self.GetSelection()))
        page = self.GetCurrentPage()

        if page.GetSizer() and not self.GetParent().IsMaximized():
            page.GetSizer().SetSizeHints(self)

        if self.GetSizer():
            self.GetSizer().SetSizeHints(self)


def main():
    app = wx.App()
    win = MainWindow()
    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
