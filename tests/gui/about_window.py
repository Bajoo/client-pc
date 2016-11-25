

class AboutWindowTestController(object):
    def __init__(self, factory, exit):
        self.view = factory(self)
        self.view.show()
        self._exit = exit

    def open_webpage_action(self, target_page):
        print('Open webpage action: page %s' % target_page)

    def bug_report_action(self):
        print('Bug report action')

    def close_action(self):
        print('Close window action.')
        self.view.destroy()
        self._exit()
