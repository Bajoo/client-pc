
from bajoo.app_status import AppStatus
from bajoo.gui.enums import ContainerStatus


class TaskBarIconTestController(object):
    def __init__(self, view_factory, exit):
        self.view = view_factory(self)
        self._exit = exit
        self.view.set_app_status(AppStatus.NOT_CONNECTED)

        print('Set initial status list ...')
        self.view.set_container_status_list([
            ('MyBajoo', '.', ContainerStatus.SYNC_DONE),
            ('Container tests', './tests', ContainerStatus.SYNC_PROGRESS),
            ('Container #2', '/container-2', ContainerStatus.SYNC_STOP)
        ])

    def primary_action(self):
        print('Execute primary action')

    def navigate_action(self, destination):
        print('Navigate to "%s"' % destination)
        print('Controller: Change status to "SYNC DONE"')
        self.view.set_app_status(AppStatus.SYNC_DONE)

    def open_container_action(self, container_path):
        print('Open container at "%s"' % container_path)
        print('Controller: Change status to "SYNC IN PROGRESS"')
        self.view.set_app_status(AppStatus.SYNC_IN_PROGRESS)

    def exit_action(self):
        print('Exit ...')
        self.view.destroy()
        self._exit()
