# -*- coding: utf-8 -*-

from ..common.i18n import _


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
        self._i18n_methods = []  # List of tuple (widget, callable, str)

    def notify_lang_change(self):
        """Notify this class that the language has changed."""

        for [method, text, format_arg] in self._i18n_methods:
            msg = _(text) if format_arg is None else _(text) % format_arg
            method(msg)

        for translator in self._i18n_child:
            translator.notify_lang_change()

    def register_i18n(self, method, value, format_arg=None):
        """Register a method to call when the language changes.

        Args:
            method (callable): method to call when the language changes.
            value (str): text to translate and to pass to the method.
            format_arg (*, optional): If set, the format '%' operator is used
                on the text with this argument.
        """
        self._i18n_methods.append((method, value, format_arg))
        msg = _(value) if format_arg is None else _(value) % format_arg
        method(msg)

    def add_i18n_child(self, widget):
        """Add a translator who will be notified when the lang changes.

        Args:
            widget (Translator): new child translator
        """
        self._i18n_child.append(widget)

    def remove_i18n(self, item):
        """Remove a registered method or a child translator from the list.

        If the item is not present, do nothing.

        Args:
            item: Either a method registered by ``register_i18n`` or a child
                added by ``add_i18n_child``.
        """
        try:
            self._i18n_child.remove(item)
        except ValueError:
            for index, [method, _1, _2] in enumerate(self._i18n_child):
                if method is item:
                    del self._i18n_child[index]
                    return

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
            self.register_i18n(getattr(window, method_name), text, format_arg)
