# -*- coding: utf-8 -*-


class AboutWindowBaseView(object):

    def __init__(self, ctrl, app_version):
        self.controller = ctrl
        self.app_version = app_version

    def show(self):
        """Show the window and set it in foreground."""
        raise NotImplementedError()

    def notify_lang_change(self):
        raise NotImplementedError()

    def is_in_use(self):
        """Determine if the window is in use.

        The Window is considered in use if it's visible.
        Returns:
            bool: True if visible; false if not.
        """
        pass

    def destroy(self):
        """Close the Window and release resources."""
        pass
