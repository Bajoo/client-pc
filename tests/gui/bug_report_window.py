

class BugReportWindowTestController(object):
    def __init__(self, factory, exit):
        self.view = factory(self)
        self.view.show()
        self._exit = exit

    def send_report_action(self, email, description):
        print('Send report action')
        print('Email is: "%s"' % email)
        print('Description is:\n%s' % description)
        if email:
            print('Display confirmation')
            self.view.display_confirmation()
        else:
            print('Dispay error')
            self.view.set_error('This is an error message!')

    def send_cancel_action(self):
        print('Send cancel action')
        self._exit()
