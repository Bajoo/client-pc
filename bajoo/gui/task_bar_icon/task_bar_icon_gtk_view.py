# -*- coding: utf-8 -*-

from functools import partial
from gi.repository import Gtk
from ...app_status import AppStatus
from ...common.i18n import _
from .task_bar_icon_base_view import (app_status_to_icon_files,
                                      app_status_to_tooltips,
                                      MenuEntry,
                                      TaskBarIconAction,
                                      TaskBarIconBaseView)


class TaskBarIconGtkView(Gtk.StatusIcon, TaskBarIconBaseView):

    def __init__(self, ctrl):
        TaskBarIconBaseView.__init__(self, ctrl)
        Gtk.StatusIcon.__init__(self)

        self._is_connected = False
        self._container_status_list = []
        self._app_status = None
        self._menu = None
        self._visible_menu = None  # cache for in-use menu object.

        self.set_title("Bajoo")

        self._handler_ids = [
            self.connect("popup-menu", self._popup_menu),
            self.connect("activate",
                         lambda _: self.controller.primary_action())
        ]

    def _popup_menu(self, _icon, button, time):
        self._build_menu()
        self._menu.popup(None, None, None, None, button, time)

    def set_app_status(self, app_status):
        """Set the general application status to display."""
        self._app_status = app_status
        self._is_connected = app_status is not AppStatus.NOT_CONNECTED

        icon_path = app_status_to_icon_files[app_status]
        self.set_from_file(icon_path)
        self.set_tooltip_text(_(app_status_to_tooltips[app_status]))
        self._build_menu()

    def notify_lang_change(self):
        """Update the view after a change of language setting."""
        self.set_tooltip_text(_(app_status_to_tooltips[self._app_status]))
        self._build_menu()

    def set_container_status_list(self, status_list):
        """Update the list of containers (and theirs status)."""
        self._container_status_list = status_list
        self._build_menu()

    def _build_menu(self):
        items_list = MenuEntry.make_menu(self._is_connected,
                                         self._container_status_list)

        if self._menu and self._menu.props.visible:
            # Save the actual menu, so the user will not see the menu
            # suddenly disappears while using it.
            self._visible_menu = self._menu

        self._menu = self._inner_build_menu(items_list)
        self._menu.show_all()

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
                                  partial(self._menu_action, m.action,
                                          m.target))

            if m.children:
                sub_gtk_menu = self._inner_build_menu(m.children)
                menu_item.set_submenu(sub_gtk_menu)

            menu_item.set_sensitive(m.enabled)
            gtk_menu.append(menu_item)

        return gtk_menu

    def _menu_action(self, action, target, _menu_item):
        """called when a menu action is triggered"""
        if action is TaskBarIconAction.OPEN_CONTAINER:
            self.controller.open_container_action(target)
        elif action is TaskBarIconAction.NAVIGATE:
            self.controller.navigate_action(target)
        elif action is TaskBarIconAction.EXIT:
            self.controller.exit_action()

    def destroy(self):
        map(self.disconnect, self._handler_ids)
        self._visible_menu = None
        self._menu = None
