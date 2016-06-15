# -*- coding: utf-8 -*-

import webbrowser
import wx
from abc import ABCMeta, abstractmethod
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import _
from .abstract_task_bar_icon import AbstractTaskBarIcon


class AbstractTaskBarIconWxInterface(object):
    __metaclass__ = ABCMeta

    OpenWindowEvent, EVT_OPEN_WINDOW = NewCommandEvent()
    RequestContainerStatus, EVT_CONTAINER_STATUS_REQUEST = NewCommandEvent()
    ExitEvent, EVT_EXIT = NewCommandEvent()

    # Possible values for OpenWindowEvent
    OpenWindowEvent_list = [AbstractTaskBarIcon.OPEN_HOME,
                            AbstractTaskBarIcon.OPEN_SUSPEND,
                            AbstractTaskBarIcon.OPEN_SHARES,
                            AbstractTaskBarIcon.OPEN_INVITATION,
                            AbstractTaskBarIcon.OPEN_SETTINGS,
                            AbstractTaskBarIcon.OPEN_ABOUT,
                            AbstractTaskBarIcon.OPEN_DEV_CONTACT]

    def __init__(self, wx_parent):
        self.wx_parent = wx_parent

    def trigger_event(self, event_id):
        if event_id in self.OpenWindowEvent_list:
            wx.PostEvent(self.wx_parent,
                         self.OpenWindowEvent(-1, target=event_id))
        elif event_id == AbstractTaskBarIcon.TASK_BAR_EXIT:
            wx.PostEvent(self.wx_parent, self.ExitEvent(-1))
        elif event_id == AbstractTaskBarIcon.OPEN_HELP:
            webbrowser.open(_('https://www.bajoo.fr/help'))
        elif event_id == AbstractTaskBarIcon.OPEN_CLIENT_SPACE:
            # TODO: set real URL
            webbrowser.open('https://www.bajoo.fr/client_space')

    def trigger_refresh_container_list(self):
        wx.PostEvent(self.wx_parent,
                     AbstractTaskBarIconWxInterface.RequestContainerStatus(-1))

    @abstractmethod
    def set_state(self, state):
        pass

    @abstractmethod
    def Destroy(self):
        pass

    @abstractmethod
    def set_container_status_list(self, status_list):
        pass
