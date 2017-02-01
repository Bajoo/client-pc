# -*- coding: utf-8 -*-

from functools import partial
import wx
from ...app_status import AppStatus
from ...common.i18n import _

from ..enums import WindowDestination
from .task_bar_icon_base_view import (app_status_to_icon_files,
                                      app_status_to_tooltips,
                                      container_status_to_icon_files,
                                      MenuEntry,
                                      TaskBarIconAction,
                                      TaskBarIconBaseView)


class TaskBarIconWxView(wx.TaskBarIcon, TaskBarIconBaseView):
    """WxPython implementation of taskBarIconView"""

    def __init__(self, ctrl):
        wx.TaskBarIcon.__init__(self)
        TaskBarIconBaseView.__init__(self, ctrl)

        self._app_status_icons = {
            key: wx.Icon(path, desiredWidth=128, desiredHeight=128) for
            (key, path) in app_status_to_icon_files.items()}

        # mapping path -> wxImage
        self._container_status_icons = {
            path: wx.Image(path) for path in
            container_status_to_icon_files.values()}

        self._app_status = None  # needed for i18n
        self._is_connected = False

        self._container_status_list = []

        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, lambda _evt: ctrl.primary_action())

    def set_app_status(self, app_status):
        self._app_status = app_status  # memorized for i18n
        self._is_connected = app_status is not AppStatus.NOT_CONNECTED
        self._set_icon_and_tooltip(app_status)

    def destroy(self):
        self.Destroy()

    def notify_lang_change(self):
        if self._app_status:
            self._set_icon_and_tooltip(self._app_status)

    def _set_icon_and_tooltip(self, app_status):
        self.SetIcon(self._app_status_icons[app_status],
                     tooltip=_(app_status_to_tooltips[app_status]))

    def CreatePopupMenu(self):
        items_list = MenuEntry.make_menu(self._is_connected,
                                         self._container_status_list)
        menu = wx.Menu()
        self._inner_create_menu(items_list, menu)
        return menu

    def _inner_create_menu(self, items_list, menu_instance):
        """Recursively build the menu.

        Args:
            items_list (List[MenuEntry]): list of entries to add in the menu.
                Can contains sub-menus.
            menu_instance (wx.Menu): parent menu, which wil contain entries.
        """
        for m in items_list:
            if m is MenuEntry.Separator:
                menu_instance.AppendSeparator()
            elif m.children:
                menu = wx.Menu()
                menu_instance.AppendMenu(wx.ID_ANY, m.title, menu)
                self._inner_create_menu(m.children, menu)
            else:
                item_id = wx.ID_ANY
                if m.action is TaskBarIconAction.EXIT:
                    item_id = wx.ID_EXIT
                elif m.action is TaskBarIconAction.NAVIGATE:
                    if m.target is WindowDestination.HOME:
                        item_id = wx.ID_HOME
                    elif m.target is WindowDestination.ABOUT:
                        item_id = wx.ID_ABOUT
                    elif m.target is WindowDestination.SETTINGS:
                        item_id = wx.ID_PREFERENCES
                elif m.target is WindowDestination.ONLINE_HELP:
                    item_id = wx.ID_HELP

                menu_item = wx.MenuItem(menu_instance, item_id, text=m.title)
                if m.icon:
                    icon = self._container_status_icons[m.icon]
                    bitmap = wx.BitmapFromImage(icon)
                    menu_item.SetBitmap(bitmap)

                menu_instance.AppendItem(menu_item)
                menu_item.Enable(m.enabled)

                if m.action:
                    self.Bind(wx.EVT_MENU, partial(self._menu_action, m),
                              menu_item)

    def _menu_action(self, menu_entry, _evt):
        """called when a menu action is triggered"""
        if menu_entry.action is TaskBarIconAction.OPEN_CONTAINER:
            self.controller.open_container_action(menu_entry.target)
        elif menu_entry.action is TaskBarIconAction.NAVIGATE:
            self.controller.navigate_action(menu_entry.target)
        elif menu_entry.action is TaskBarIconAction.EXIT:
            self.controller.exit_action()

    def set_container_status_list(self, status_list):
        self._container_status_list = status_list
