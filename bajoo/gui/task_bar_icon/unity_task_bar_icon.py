# -*- coding: utf-8 -*-

import pickle
import sys
from threading import Thread
from os.path import abspath

import gtk
import gobject
import appindicator


from functools import partial

from ...common.i18n import set_lang, _
from .abstract_task_bar_icon import AbstractTaskBarIcon
from .unity_data_exchange import UnityDataExchange  # noqa

APPINDICATOR_ID = 'bajoo'


def print_to_stdout(value):
    if not sys.stdout.closed:
        sys.stdout.write(value+"\n")
        sys.stdout.flush()


class UnityTaskBarIcon(AbstractTaskBarIcon):
    def __init__(self):
        AbstractTaskBarIcon.__init__(self)

        self.indicator = None
        gobject.idle_add(self._create_indicator)

        self.set_state(self.NOT_CONNECTED)

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
            self._icons[self.NOT_CONNECTED],
            appindicator.CATEGORY_SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

    def set_container_status_list(self, status_list):
        """
            This override is needed because the libappindicator does not
            rebuild the menu on each mouse clic and so it needs to be rebuilt
            on each menu update.
        """
        AbstractTaskBarIcon.set_container_status_list(self, status_list)
        self.build_menu()

    def set_state(self, state):
        AbstractTaskBarIcon.set_state(self, state)
        self.build_menu()

    def set_lang(self, lang):
        set_lang(lang)
        self.build_menu()

    def set_icon(self, icon, tooltip=None):
        gobject.idle_add(self._set_icon, abspath(icon))

    def _set_icon(self, icon):
        self.indicator.set_icon(icon)

    def _inner_build_menu(self, items_list):
        gtk_menu = gtk.Menu()
        for m in items_list:
            if m is None:
                gtk_menu.append(gtk.SeparatorMenuItem())
                continue

            if m.icon is None:
                menu_item = gtk.MenuItem(_(m.title))
            else:
                menu_item = gtk.ImageMenuItem()
                menu_item.set_label(_(m.title))

                img = gtk.Image()
                img.set_from_file(m.icon)
                menu_item.set_image(img)
                menu_item.set_always_show_image(True)

            if m.event_handler is None:
                menu_item.connect('activate',
                                  partial(self.clic_event, m.menu_id))
            else:
                menu_item.connect('activate', m.event_handler)

            if m.children is not None:
                sub_gtk_menu = self._inner_build_menu(m.children)
                menu_item.set_submenu(sub_gtk_menu)

            if not m.enabled:
                menu_item.set_sensitive(False)

            gtk_menu.append(menu_item)

        return gtk_menu

    def build_menu(self):
        menus = self._getMenuItems()
        gtk_menu = self._inner_build_menu(menus)
        gtk_menu.show_all()

        gobject.idle_add(self._build_menu, gtk_menu)

    def _build_menu(self, menu):
        self.indicator.set_menu(menu)

    def clic_event(self, menu_id, event):
        print_to_stdout("event id %s" % menu_id)

        if menu_id == AbstractTaskBarIcon.TASK_BAR_EXIT:
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
