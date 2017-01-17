

class ChangePasswordWindowTestController(object):
    def __init__(self, factory, exit):
        self.view = factory(self, None)
        self._exit = exit
        self.view.show_modal()  # Note: may be blocking
        # TODO: on wx, show_modal() is blocking; exit() don't work when called
        # from the modal context (and send_cancel_action is called from modal
        # context)

    def change_password_action(self, old_password, new_password):
        print('Change password action from "%s" to "%s"' %
              (old_password, new_password))
        self.view.show_error('This is an error message!')

    def send_cancel_action(self):
        print('View has sent a CANCEL action')
        self.view.destroy()
        self._exit()
