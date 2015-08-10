# -*- coding: utf-8 -*-

from functools import partial
import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ..base_view import BaseView
from . import AdvancedSettingsTab
from . import GeneralSettingsTab
from . import NetworkSettingsTab


class SettingsTab(wx.Panel):
    """Panel containing all settings.

    The settings are subdivided into 3 categories, each category has a panel
    associated.

    This class display them using a wx.Notebook object, and manages the 'Ok',
    'Apply' and 'Cancel' buttons.

    Attributes:
        EVT_CONFIG_REQUEST (int): wx.Event emited when the class need data to
            display. It's expected to receive the data from the `load_config`
            method.
    """

    ConfigRequest, EVT_CONFIG_REQUEST = NewCommandEvent()

    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        self._view = SettingsTabView(self)

        self.Bind(wx.EVT_BUTTON, self._valid_changes, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self._cancel_changes, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._apply_changes, id=wx.ID_APPLY)

    def Show(self, show=True):
        if show:
            wx.PostEvent(self, self.ConfigRequest(self.GetId()))
        wx.Panel.Show(self, show)

    def load_config(self, config=None):
        for tab in ('general', 'network', 'advanced'):
            self.FindWindow(tab).load_config(config)

    def _cancel_changes(self, _event):
        """Button cancel: reset the form and quit."""
        self.load_config()
        self.GetTopLevelParent().Close()

    def _apply_changes(self, _event):
        """Button Apply: update the settings"""
        for tab in ('general', 'network', 'advanced'):
            self.FindWindow(tab)._on_applied(_event)

    def _valid_changes(self, _event):
        """Apply changes and close window."""
        self._apply_changes(_event)
        self.GetTopLevelParent().Close()


class SettingsTabView(BaseView):

    def __init__(self, window):
        BaseView.__init__(self, window)
        notebook = wx.Notebook(self.window)

        general = GeneralSettingsTab(notebook, name='general')
        network = NetworkSettingsTab(notebook, name='network')
        advanced = AdvancedSettingsTab(notebook, name='advanced')
        notebook.AddPage(general, '')
        notebook.AddPage(network, '')
        notebook.AddPage(advanced, '')

        # i18n
        set_tab_name = notebook.SetPageText
        self.register_i18n(partial(set_tab_name, 0), N_('General settings'))
        self.register_i18n(partial(set_tab_name, 1), N_('Network settings'))
        self.register_i18n(partial(set_tab_name, 2), N_('Advanced settings'))
        self.add_i18n_child(general)
        self.add_i18n_child(network)
        self.add_i18n_child(advanced)

        button_sizer_box = self.create_settings_button_box(self.window)

        # sizer
        sizer = self.make_sizer(wx.VERTICAL,
                                [notebook, None, button_sizer_box],
                                flag=wx.EXPAND)
        self.window.SetSizer(sizer)
