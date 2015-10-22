# -*- coding: utf-8 -*-
from os import path

import wx
from wx.lib.filebrowsebutton import DirBrowseButton


class ShareLocationBrowser(DirBrowseButton):
    """
    Derive the class DirBrowseButton to apply the share name as child folder
    each time user changes the directory by clicking "Browse".

    This class is created because wx does not supply an "EVT_BROWSE" event.
    """

    def __init__(self, **kwargs):
        DirBrowseButton.__init__(
            self, changeCallback=self._on_changed, **kwargs)

        self._share_name = ''
        self._parent_folder = kwargs.get('startDirectory', '.')

    def _on_changed(self, __event):
        self._post_text_event()

    def _post_text_event(self):
        """
        Redirect both events when user clicks button "Browse"
        or changes the text to the wx.EVT_TEXT event.
        """
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_UPDATED)
        evt.SetEventObject(self)
        evt.SetId(self.GetId())

        wx.PostEvent(self, evt)

    def OnBrowse(self, event=None):
        """
        After browsing for parent directory of the share, apply the
        share name as child directory
        """
        DirBrowseButton.OnBrowse(self, event)
        self._parent_folder = self.GetValue()
        self.SetValue(path.join(self._parent_folder, self._share_name))

        self._post_text_event()

    def set_share_name(self, share_name, set_value_now=True):
        """
        Change the share name, this should be called each time user
        changes the share name value.

        Args:
            set_value_now (boolean):
                Change the location value immediately
        """
        self._share_name = share_name

        if set_value_now:
            self.SetValue(path.join(self._parent_folder, self._share_name))
