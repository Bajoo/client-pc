# -*- coding: utf-8 -*-

from functools import partial
from gi.repository import Gdk, Gtk

from ....common.i18n import _
from ....common.path import resource_filename
from .about_window_controller import Page
from .about_window_base_view import AboutWindowBaseView


class AboutWindowGtkView(Gtk.Window, AboutWindowBaseView):

    def __init__(self, ctrl):
        AboutWindowBaseView.__init__(self, ctrl)
        Gtk.Window.__init__(self)

        icon = resource_filename('assets/window_icon.png')
        self.set_icon_from_file(icon)

        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA())
        primary_box = Gtk.Box()
        self.add(primary_box)

        banner_path = resource_filename('assets/images/side_banner.png')
        banner = Gtk.Image.new_from_file(banner_path)
        banner_gb_color = Gdk.RGBA()
        banner_gb_color.parse('#FD6533')
        banner.override_background_color(Gtk.StateFlags.NORMAL,
                                         banner_gb_color)
        primary_box.add(banner)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=20,
                              spacing=15)
        primary_box.add(content_box)

        title_label = Gtk.Label(use_markup=True)
        title_label.set_label('<span font="28" ><b>Bajoo 2</b></span>')
        self._subtitle_label = Gtk.Label(use_markup=True)
        self._version_label = Gtk.Label(use_markup=True, xalign=0)
        self._faq_label = Gtk.Label(use_markup=True, xalign=0)
        self._contact_label = Gtk.Label(use_markup=True, xalign=0)
        self._description_label = Gtk.Label(use_markup=True, wrap=True,
                                            xalign=0)
        self._dependencies_label = Gtk.Label(xalign=0)

        self._contact_label.connect('activate-link', self._contact_link_event)

        for child in (title_label, self._subtitle_label, self._version_label,
                      self._faq_label, self._contact_label,
                      self._description_label, self._dependencies_label):
            content_box.add(child)

        dependencies_list = Gtk.Box(spacing=10)
        content_box.add(dependencies_list)

        deps = [
            ('WxPython', 'http://www.wxpython.org'),
            ('appdirs', 'https://pypi.python.org/pypi/appdirs'),
            ('requests', 'http://python-requests.org'),
            ('futures', 'https://pypi.python.org/pypi/futures'),
            ('python-gnupg', 'https://pypi.python.org/pypi/gnupg'),
            ('watchdog', 'https://pypi.python.org/pypi/watchdog'),
            ('pysocks', 'https://pypi.python.org/pypi/PySocks'),
            ('notify2', 'https://pypi.python.org/pypi/notify2'),
            ('pypiwin32', 'https://pypi.python.org/pypi/pypiwin32')
        ]

        for name, url in deps:
            label = Gtk.Label(use_markup=True)
            label.set_label('<a href="%s" >%s</a>' % (url, name))
            dependencies_list.add(label)

        self._trademark_label = Gtk.Label()
        self._website_label = Gtk.Label(use_markup=True)
        content_box.add(self._trademark_label)
        content_box.add(self._website_label)

        social_network_list = {
            Page.GPLUS: 'assets/images/google-plus.png',
            Page.FACEBOOK: 'assets/images/facebook.png',
            Page.TWITTER: 'assets/images/twitter.png'
        }
        social_network_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                     margin=15)
        primary_box.pack_end(social_network_box, False, False, 0)
        social_network_inner_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=15)
        social_network_box.pack_start(social_network_inner_box, True, False, 0)

        for (target_page, image_path) in social_network_list.items():
            image = Gtk.Image.new_from_file(resource_filename(image_path))
            btn = Gtk.Button(image=image, relief=Gtk.ReliefStyle.NONE)
            social_network_inner_box.add(btn)

            callback = partial(self._social_network_button_clicked,
                               target_page)
            btn.connect('clicked', callback)

        self.connect('delete-event', self._delete_event)

        self._set_all_labels()

    def show(self):
        """Show the window and set it in foreground."""
        Gtk.Window.show_all(self)

    def notify_lang_change(self):
        self._set_all_labels()

    def is_in_use(self):
        return self.props.visible

    def destroy(self):
        Gtk.Window.destroy(self)

    def _contact_link_event(self, _label, uri):
        # This event can be called on legit URL. On these cases, returning
        # False will let the default behavior occurs.
        if uri == 'bajoo://report-bug':
            self.controller.bug_report_action()
            return True
        return False

    def _delete_event(self, _target, _event):
        self.controller.close_action()
        return False

    def _social_network_button_clicked(self, target_page, _button):
        self.controller.open_webpage_action(target_page)

    def _set_all_labels(self):
        self.props.title = _('About Bajoo')

        mapping_widget_text = {
            self._subtitle_label:
                _('<i>Official software for Bajoo online storage service</i>'),
            self._version_label:
                _('Version: <span font="10"><b>%s</b></span>' %
                  self.app_version),
            self._description_label:
                _('This software is distributed under the terms of the MIT'
                  ' License.\n It is freely redistributable, the source code '
                  'is available '
                  '<a href="https://www.github.com/bajoo/client-pc">on '
                  'GitHub</a>.'),
            self._trademark_label: _('Bajoo is a registered trademark.'),
            self._website_label:
                _('<a href="https://www.bajoo.fr" >www.bajoo.fr</a>'),
            self._faq_label:
                _('<a href="https://www.bajoo.fr/partage-de-dossiers" >List of'
                  ' frequently asked questions.</a>'),
            self._contact_label:
                _('If you have a new question, feel free to '
                  '<a href="https://www.bajoo.fr/contact" >contact us</a> or '
                  '<a href="bajoo://report-bug" >report a problem</a>.'),
            self._dependencies_label: _('Bajoo uses the following libraries:')
        }

        for widget, text in mapping_widget_text.items():
            widget.set_label(text)
