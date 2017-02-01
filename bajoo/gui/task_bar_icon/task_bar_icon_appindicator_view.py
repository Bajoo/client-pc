# -*- coding: utf-8 -*-

from os.path import abspath
from functools import partial

from ...app_status import AppStatus
from .task_bar_icon_base_view import (app_status_to_icon_files, MenuEntry,
                                      TaskBarIconAction, TaskBarIconBaseView)

import gi
gi.require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3, GObject, Gtk  # noqa


APPINDICATOR_ID = 'bajoo'


class TaskBarIconAppIndicatorView(TaskBarIconBaseView):
    """Implementation of task bar icon using libappindicator.

    Notes:
        The menu is build once, then reused at each click on the trayicon
        (by opposite to other libraries like wxPython who rebuild the menu at
        each display). We rebuild the menu only on explicit changes.

    """
    def __init__(self, ctrl):
        TaskBarIconBaseView.__init__(self, ctrl)
        self.indicator = AppIndicator3.Indicator.new(
            APPINDICATOR_ID,
            app_status_to_icon_files[AppStatus.NOT_CONNECTED],
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self._is_connected = False
        self._container_status_list = []
        self.set_app_status(AppStatus.NOT_CONNECTED)

    def set_app_status(self, app_status):
        self._is_connected = app_status != AppStatus.NOT_CONNECTED
        icon_path = abspath(app_status_to_icon_files[app_status])
        self.indicator.set_icon(icon_path)
        self.build_menu()

    def notify_lang_change(self):
        self.build_menu()

    def set_container_status_list(self, status_list):
        self._container_status_list = status_list
        self.build_menu()

    def _inner_build_menu(self, items_list):
        gtk_menu = Gtk.Menu()
        for m in items_list:
            if m is MenuEntry.Separator:
                gtk_menu.append(Gtk.SeparatorMenuItem())
                continue

            if m.icon is None:
                menu_item = Gtk.MenuItem(m.title)
            else:
                menu_item = Gtk.ImageMenuItem()
                menu_item.set_label(m.title)

                # TODO: try to reuse Image !!!
                img = Gtk.Image()
                img.set_from_file(m.icon)
                menu_item.set_image(img)
                menu_item.set_always_show_image(True)

            if m.action:
                menu_item.connect('activate',
                                  partial(self.clic_event, m.action, m.target))

            if m.children:
                sub_gtk_menu = self._inner_build_menu(m.children)
                menu_item.set_submenu(sub_gtk_menu)

            if not m.enabled:
                menu_item.set_sensitive(False)

            gtk_menu.append(menu_item)

        return gtk_menu

    def build_menu(self):
        items_list = MenuEntry.make_menu(self._is_connected,
                                         self._container_status_list)
        gtk_menu = self._inner_build_menu(items_list)
        gtk_menu.show_all()
        self.indicator.set_menu(gtk_menu)

    def clic_event(self, action, target, _event):
        """called when a menu action is triggered"""

        if action == TaskBarIconAction.OPEN_CONTAINER:
            self.controller.open_container_action(target)
        elif action == TaskBarIconAction.NAVIGATE:
            self.controller.navigate_action(target)
        elif action == TaskBarIconAction.EXIT:
            self.controller.exit_action()
        return False
