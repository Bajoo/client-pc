# -*- coding: utf-8 -*-
from os import path

from wx.lib.filebrowsebutton import DirBrowseButton


class ShareLocationBrowser(DirBrowseButton):
    """
    Derive the class DirBrowseButton to apply the share name as child folder
    each time user changes the directory by clicking "Browse".

    This class is created because wx does not supply an "EVT_BROWSE" event.
    """

    def __init__(self, **kwargs):
        """Create the DemoPanel."""
        DirBrowseButton.__init__(self, **kwargs)

        self._share_name = ''
        self._parent_folder = kwargs.get('startDirectory', '.')

    def OnBrowse(self, event=None):
        """
        After browsing for parent directory of the share, apply the
        share name as child directory
        """
        DirBrowseButton.OnBrowse(self, event)
        self._parent_folder = self.GetValue()
        self.SetValue(path.join(self._parent_folder, self._share_name))

    def set_share_name(self, share_name):
        """
        Change the share name, this should be called each time user
        changes the share name value.
        """
        self._share_name = share_name
        self.SetValue(path.join(self._parent_folder, self._share_name))
