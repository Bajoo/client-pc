# -*- coding: utf-8 -*-

import logging

import wx

from ..common.i18n import _

_logger = logging.getLogger(__name__)


class Translator(object):
    """Utility for GUI class who performs automatic translation on lang change.

    A list of method is registered, associated to the untranslated values to
    apply.
    These methods are called when the register_i18n method is called, and each
    time the language changes.

    It's possible to add another instance of Translator as child, to delegate
    the translation (useful when using nested user-defined widgets).

    The lang change must be notified by calling ``notify_lang_change``.

    When a widget is deleted of its parent class, it should be removed (or its
    registered methods) from the translation list, by calling ``remove_i18n``.
    """

    def __init__(self):
        self._i18n_child = []
        self._i18n_methods = {}  # dict of tuple win:(callable, str, args)
        self._callbacks = []  # List of functions

    def _on_window_destroy(self, event):
        window = event.GetWindow()
        self._i18n_methods.pop(window, None)

    def notify_lang_change(self):
        """Notify this class that the language has changed."""

        for window, value in self._i18n_methods.items():

            # check if the python object is still linked to a C++ object
            if not window:
                self._i18n_methods.pop(window, None)
                continue

            method, text, format_arg = value
            msg = _(text) if format_arg is None else _(text) % format_arg
            method(msg)

        for translator in self._i18n_child:
            translator.notify_lang_change()

        for (cb, instance) in self._callbacks:
            cb(instance)

    def register_i18n(self, window, method, value, format_arg=None):
        """Register a method to call when the language changes.

        Args:
            method (callable): method to call when the language changes.
            value (str): text to translate and to pass to the method.
            format_arg (*, optional): If set, the format '%' operator is used
                on the text with this argument.
        """

        if isinstance(window, wx.Window):
            window.Bind(wx.EVT_WINDOW_DESTROY, self._on_window_destroy)
        elif hasattr(window, 'GetOwner'):
            window = window.GetOwner()
            window.Bind(wx.EVT_WINDOW_DESTROY, self._on_window_destroy)
        elif isinstance(window, wx.TaskBarIcon):
            pass  # not a window, no destroy event, same lifetime as the app
        else:
            _logger.warning("Not possible to bind a graphical object in the "
                            "translator system: %s" % str(type(window)))

        self._i18n_methods[window] = (method, value, format_arg,)
        msg = _(value) if format_arg is None else _(value) % format_arg
        method(msg)

    def add_i18n_child(self, widget):
        """Add a translator who will be notified when the lang changes.

        Args:
            widget (Translator): new child translator
        """
        self._i18n_child.append(widget)

    def remove_i18n_child(self, widget):
        """Remove a registered child translator from the list.

        If the item is not present, do nothing.

        Args:
            item: a child dded by ``add_i18n_child``.
        """

        try:
            self._i18n_child.remove(widget)
        except ValueError:
            pass

    def register_many_i18n(self, method_name, windows):
        """register many i18n window who shares a common method.

        Args:
            method_name (str): method member of each window.
            windows (list of item): each item can be either the text to
                translate, or a tuple (text, format_arg) with format_arg an
                argument to pass to the '%' operator applied on text.
        """
        for (window, text) in windows.items():
            format_arg = None
            if isinstance(text, tuple):
                text, format_arg = text
            self.register_i18n(window,
                               getattr(window, method_name),
                               text,
                               format_arg)

    @staticmethod
    def i18n_callback(f):
        """Decorator who call the method each time the language changes.

        The first the f method is called, its registered in the i18n methods.
        Each time the language changes, the f method is called.

        Args:
            f (callable): must take one argument `self`, instance of
                Translator.
        """
        def wrapper(self):
            if (f, self) not in self._callbacks:
                self._callbacks.append((f, self))

            return f(self)

        return wrapper
