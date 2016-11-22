# -*- coding: utf-8 -*-

import logging
import pickle
import subprocess
import sys
from threading import Thread
from ...common.i18n import get_lang
from .base import TaskBarIconBaseView
from .common_view_data import TaskBarIconAction
from .unity_data_exchange import UnityDataExchange

_logger = logging.getLogger(__name__)


class UnityAdapterView(TaskBarIconBaseView):
    """Adapter between the controller and the Unity process-separated view.

    It implements the Task Bar icon interface, and relay all messages to the
    real implementation (which is located in a distinct process, due to
    incompatibilities between wxPython and Unity).

    Messages are passed through stdin/stdout of the new process.
    """

    def __init__(self, ctrl):
        TaskBarIconBaseView.__init__(self, ctrl)

        args = (sys.executable, "-m",
                "bajoo.gui.task_bar_icon.unity_task_bar_icon",)

        self.process = subprocess.Popen(args=args,
                                        bufsize=1,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        close_fds=True)
        self._refresh_running = True
        self._is_connected = False

        thread = Thread(target=self._read_process_stdout)
        thread.daemon = True
        thread.start()

        # The unity process don't have the lang setting at start. We call
        # notify_lang once at start to send it.
        self.notify_lang_change()

    def _read_process_stdout(self):
        while self._refresh_running:
            try:
                line = self.process.stdout.readline()
            except ValueError:
                self.destroy()
                break

            if line is not None:
                line = line.strip()

            if line.startswith("event "):
                try:
                    action, target = line.split(' ')[1:]
                except ValueError:
                    continue
                else:
                    self._process_event(action, target)
            else:
                _logger.error(line)

    def set_app_status(self, app_status):
        self._send_object(UnityDataExchange(state=app_status))

    def destroy(self):
        self._refresh_running = False
        self.process.stdin.close()
        self.process.stdout.close()

    def notify_lang_change(self):
        lang = get_lang()
        if lang is not None:
            self._send_object(UnityDataExchange(lang=lang))

    def _process_event(self, action, target):
        """called when a menu action is triggered"""

        if action == TaskBarIconAction.OPEN_CONTAINER:
            self.controller.open_container_action(target)
        elif action == TaskBarIconAction.NAVIGATE:
            self.controller.navigate_action(target)
        elif action == TaskBarIconAction.EXIT:
            self.controller.exit_action()

    def set_container_status_list(self, status_list):
        self._send_object(UnityDataExchange(status_list=status_list))

    def _send_object(self, obj):
        if not self.process.stdin.closed:
            obj_string = pickle.dumps(obj)
            self.process.stdin.write("object size %s\n" % len(obj_string))
            self.process.stdin.write(obj_string)
            self.process.stdin.flush()


def main():
    import logging
    from ...app_status import AppStatus
    from .base import ContainerStatus
    logging.basicConfig()

    class Controller(object):
        def __init__(self, View):
            self.view = View(self)
            self.view.set_app_status(AppStatus.NOT_CONNECTED)
            self.view.set_container_status_list([
                ('MyBajoo', '.', ContainerStatus.SYNC_DONE),
                ('Container tests', './tests', ContainerStatus.SYNC_PROGRESS),
                ('Container #2', '/container-2', ContainerStatus.SYNC_STOP)
            ])
            print('ok')

        def primary_action(self):
            print('Execute primary action')

        def navigate_action(self, destination):
            print('Navigate to "%s"' % destination)
            self.view.set_app_status(AppStatus.SYNC_DONE)

        def open_container_action(self, container_path):
            print('Open container at "%s"' % container_path)
            self.view.set_app_status(AppStatus.SYNC_DONE)

        def exit_action(self):
            print('Exit ...')
            self.view.destroy()

    c = Controller(UnityAdapterView)
    c.view.process.wait()


if __name__ == '__main__':
    main()
