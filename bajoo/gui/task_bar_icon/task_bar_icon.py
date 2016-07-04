# -*- coding: utf-8 -*-

import logging
from os.path import abspath

import wx

from bajoo.common.i18n import _
from bajoo.common.util import open_folder
from ..translator import Translator
from .abstract_task_bar_icon import AbstractTaskBarIcon
from .abstract_task_bar_icon_wx_interface import AbstractTaskBarIconWxInterface

_logger = logging.getLogger(__name__)


def _create_event_mapping(mapping_open_evt):
    FROM_WX_TO_EVT = {}
    FROM_EVT_TO_WX = {}

    for wx_id, event_id in mapping_open_evt:
        FROM_WX_TO_EVT[wx_id] = event_id
        FROM_EVT_TO_WX[event_id] = wx_id

    # special case, open home on wx_event -1
    FROM_WX_TO_EVT[-1] = AbstractTaskBarIcon.OPEN_HOME

    return FROM_WX_TO_EVT, FROM_EVT_TO_WX


class TaskBarIcon(wx.TaskBarIcon,
                  AbstractTaskBarIcon,
                  AbstractTaskBarIconWxInterface,
                  Translator):
    """Task bar icon of the Bajoo app

    The trayicon send an ExitEvent when the user want to quit.
    When the user click on a menu to open a window, an event OpenWindowEvent
    is emitted.

    """

    # IDs for menu entries
    ID_SUSPEND_SYNC = wx.NewId()
    ID_MANAGE_SHARES = wx.NewId()
    ID_CLIENT_SPACE = wx.NewId()
    ID_INVITATION = wx.NewId()
    ID_HELP = wx.NewId()
    ID_SETTINGS = wx.NewId()
    ID_DEV_CONTACT = wx.NewId()
    ID_HOME = wx.ID_HOME
    ID_ABOUT = wx.ID_ABOUT
    ID_EXIT = wx.ID_EXIT

    mapping_open_evt = [
        (ID_SUSPEND_SYNC, AbstractTaskBarIcon.OPEN_SUSPEND,),
        (ID_MANAGE_SHARES, AbstractTaskBarIcon.OPEN_SHARES,),
        (ID_SETTINGS, AbstractTaskBarIcon.OPEN_SETTINGS,),
        (ID_INVITATION, AbstractTaskBarIcon.OPEN_INVITATION,),
        (ID_ABOUT, AbstractTaskBarIcon.OPEN_ABOUT,),
        (ID_HOME, AbstractTaskBarIcon.OPEN_HOME,),
        (ID_DEV_CONTACT, AbstractTaskBarIcon.OPEN_DEV_CONTACT,),
        (ID_HELP, AbstractTaskBarIcon.OPEN_HELP,),
        (ID_CLIENT_SPACE, AbstractTaskBarIcon.OPEN_CLIENT_SPACE,),
        (ID_EXIT, AbstractTaskBarIcon.TASK_BAR_EXIT,)
    ]

    FROM_WX_TO_EVT, FROM_EVT_TO_WX = _create_event_mapping(mapping_open_evt)

    def __init__(self):
        wx.TaskBarIcon.__init__(self)
        AbstractTaskBarIcon.__init__(self)
        AbstractTaskBarIconWxInterface.__init__(self, self)
        Translator.__init__(self)

        # convert icon path to wx object
        new_icon = {}
        for key, path in self._icons.items():
            new_icon[key] = wx.Icon(path)

        self._icons = new_icon

        # convert container icon path to wx object
        new_container_icons = {}
        for key, path in self._container_icons.items():
            new_container_icons[key] = wx.Image(abspath(path))

        self._container_icons = new_container_icons

        self.set_state(self.NOT_CONNECTED)

        self.register_i18n(
            self,
            lambda txt: self.SetIcon(self._icons[self._state], tooltip=txt),
            self._tooltips[self._state])

        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self._open_root_folder)
        self.Bind(wx.EVT_MENU,
                  lambda _evt: wx.PostEvent(self, self.ExitEvent(-1)),
                  id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self._open_window)

    def _open_root_folder(self, event):
        if wx.GetApp().user_profile is not None:
            # User connected, open the root folder
            open_folder(wx.GetApp().user_profile.root_folder_path)
        else:
            # User not connected, open the connection window
            wx.PostEvent(
                self,
                self.OpenWindowEvent(-1, target=AbstractTaskBarIcon.OPEN_HOME))

    def _open_window(self, event):
        event_id = event.GetId()

        if event_id in self.FROM_WX_TO_EVT:
            self.trigger_event(self.FROM_WX_TO_EVT[event_id])
        else:
            event.Skip()

    def _inner_create_menu(self, items_list, menu_instance, parent=None):
        for m in items_list:
            if m is None:
                menu_instance.AppendSeparator()
                continue

            if m.menu_id > 0:
                wx_id = self.FROM_EVT_TO_WX[m.menu_id]
            else:
                wx_id = m.menu_id  # no op id

            if m.children is not None and len(m.children) > 0:
                menu = wx.Menu()
                menu_instance.AppendMenu(-1, _(m.title), menu)
                self._inner_create_menu(m.children, menu)
            else:
                menu_item = wx.MenuItem(menu_instance, wx_id, _(m.title))
                menu_instance.AppendItem(menu_item)

                if m.event_handler is not None:
                    self.Bind(wx.EVT_MENU, m.event_handler, menu_item)

                # FIXME seems to be broken for share icons
                if m.icon is not None:
                    bitmap = wx.BitmapFromImage(m.icon)
                    menu_item.SetBitmap(bitmap)

            if not m.enabled:
                menu_item.Enable(False)

    def CreatePopupMenu(self):
        if self._is_connected:
            self.trigger_refresh_container_list()

        items_list = self._getMenuItems()
        menu = wx.Menu()
        self._inner_create_menu(items_list, menu)
        return menu

    def set_icon(self, icon, tooltip=None):
        self.SetIcon(icon, tooltip=_(tooltip))


def main():
    app = wx.App()

    def exit(_):
        print("exit wx mainloop")
        app.ExitMainLoop()

    def open_win(event):
        print("open win: %s" % event.target)

    def container_status(_):
        print("get container status")

    app.Bind(AbstractTaskBarIconWxInterface.EVT_OPEN_WINDOW, open_win)
    app.Bind(AbstractTaskBarIconWxInterface.EVT_EXIT, exit)
    app.Bind(AbstractTaskBarIconWxInterface.EVT_CONTAINER_STATUS_REQUEST,
             container_status)

    wx.Frame(None)
    task_bar = TaskBarIcon()
    task_bar.set_state(AbstractTaskBarIcon.SYNC_DONE)
    app.MainLoop()

if __name__ == '__main__':
    main()
