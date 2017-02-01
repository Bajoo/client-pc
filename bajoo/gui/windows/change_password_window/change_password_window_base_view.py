

class ChangePasswordWindowBaseView(object):

    def __init__(self, ctrl, parent):
        """

        Args:
            ctrl (ChangePasswordWindowController): controller
            parent: parent Window. Must be a View.
        """
        self.controller = ctrl

    def is_in_use(self):
        pass

    def destroy(self):
        """Destroy the window"""
        pass

    def show(self):
        pass

    def notify_lang_change(self):
        pass

    def show_error(self, message):
        """Show an error message

        Args:
            message (Text): error message, already translated in the user
                language.
        """
        pass

    def show_modal(self):
        """Show the Window, and make it modal."""
        pass
