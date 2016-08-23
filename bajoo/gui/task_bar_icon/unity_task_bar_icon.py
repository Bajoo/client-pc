# -*- coding: utf-8 -*-

import pickle
import sys
from threading import Thread
from os.path import abspath

import gtk
import gobject
import appindicator

from functools import partial

from ...app_status import AppStatus
from ...common.i18n import set_lang
from .unity_data_exchange import UnityDataExchange  # noqa
from .common_view_data import (app_status_to_icon_files, MenuEntry,
                               TaskBarIconAction)

APPINDICATOR_ID = 'bajoo'


def print_to_stdout(value):
    if not sys.stdout.closed:
        sys.stdout.write(value+"\n")
        sys.stdout.flush()


class UnityTaskBarIcon(object):
    """Implementation of task bar icon using libappindicator.

    It's intended to be created and used by UnityAdapterView.

    Notes:
        The menu is build once, then reused at each click on the trayicon
        (by opposite to other libraries like wxPython who rebuild the menu at
        each display). We rebuild the menu only on explicit changes.

    """
    def __init__(self):

        self.indicator = None
        gobject.idle_add(self._create_indicator)

        self._is_connected = False
        self._container_status_list = []
        self.set_state(AppStatus.NOT_CONNECTED)

        self.read_stdin = True
        thread = Thread(target=self._read_process_stdin)
        thread.start()

    def _read_process_stdin(self):
        while self.read_stdin:
            try:
                line = sys.stdin.readline()
            except ValueError:
                self._exit()
                break

            if line is not None:
                line = line.strip()

            if line is None or len(line) == 0:
                self._exit()
                break

            if line.startswith("object size "):
                try:
                    object_size = int(line[12:])
                except ValueError:
                    continue

                object_string = ""

                while object_size > 0:
                    try:
                        object_string_part = sys.stdin.read(object_size)
                    except ValueError:
                        break

                    object_string_part_size = len(object_string_part)

                    if object_string_part_size == 0:
                        break

                    object_size -= len(object_string_part)
                    object_string += object_string_part

                if object_size == 0:
                    try:
                        data = pickle.loads(object_string)
                    except:
                        continue

                    if data.status_list is not None:
                        self.set_container_status_list(data.status_list)

                    if data.state is not None:
                        self.set_state(data.state)

                    if data.lang is not None:
                        self.set_lang(data.lang)

    def _create_indicator(self):
        self.indicator = appindicator.Indicator(
            APPINDICATOR_ID,
            app_status_to_icon_files[AppStatus.NOT_CONNECTED],
            appindicator.CATEGORY_SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

    def set_container_status_list(self, status_list):
        self._container_status_list = status_list
        self.build_menu()

    def set_state(self, state):
        self._is_connected = state != AppStatus.NOT_CONNECTED
        icon_path = abspath(app_status_to_icon_files[state])
        gobject.idle_add(self._set_icon, icon_path)
        self.build_menu()

    def set_lang(self, lang):
        set_lang(lang)
        self.build_menu()

    def _set_icon(self, icon):
        self.indicator.set_icon(icon)

    def _inner_build_menu(self, items_list):
        gtk_menu = gtk.Menu()
        for m in items_list:
            if m is MenuEntry.Separator:
                gtk_menu.append(gtk.SeparatorMenuItem())
                continue

            if m.icon is None:
                menu_item = gtk.MenuItem(m.title)
            else:
                menu_item = gtk.ImageMenuItem()
                menu_item.set_label(m.title)

                # TODO: try to reuse Image !!!
                img = gtk.Image()
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

        gobject.idle_add(self._build_menu, gtk_menu)

    def _build_menu(self, menu):
        self.indicator.set_menu(menu)

    def clic_event(self, action, target, _event):
        print_to_stdout("event %s %s" % (action, target))

        if action == TaskBarIconAction.EXIT:
            self._exit()

        return False

    def _exit(self):
        self.read_stdin = False
        sys.stdin.close()
        sys.stdout.close()
        gtk.main_quit()


def main():
    gobject.threads_init()
    UnityTaskBarIcon()
    gtk.main()


if __name__ == '__main__':
    main()
