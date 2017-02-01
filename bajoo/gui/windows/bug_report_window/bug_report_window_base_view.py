

class BugReportWindowBaseView(object):

    def __init__(self, ctrl):
        self.controller = ctrl

    def is_in_use(self):
        pass

    def destroy(self):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def notify_lang_change(self):
        pass

    def enable_form(self):
        pass

    def disable_form(self):
        pass

    def set_error(self, message):
        pass

    def display_confirmation(self):
        pass
