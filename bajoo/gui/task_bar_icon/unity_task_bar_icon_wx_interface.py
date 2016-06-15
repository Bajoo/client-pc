# -*- coding: utf-8 -*-

import pickle
import subprocess
import logging
import sys
from threading import Thread, Timer

from ...common.i18n import get_lang
from .abstract_task_bar_icon_wx_interface import AbstractTaskBarIconWxInterface
from bajoo.gui.task_bar_icon.abstract_task_bar_icon import AbstractTaskBarIcon
from .unity_data_exchange import UnityDataExchange

_logger = logging.getLogger(__name__)

CONTAINER_STATUS_REFRESH_DELAY = 12.3456


class UnityTaskBarIconWxInterface(AbstractTaskBarIconWxInterface):
    def __init__(self, wx_parent):
        AbstractTaskBarIconWxInterface.__init__(self, wx_parent)

        args = (sys.executable,
                "-m",
                "bajoo.gui.task_bar_icon.unity_task_bar_icon",)
        self.process = subprocess.Popen(args=args,
                                        bufsize=1,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        close_fds=True)

        self._is_connected = False
        self._refresh_running = True
        thread = Thread(target=self._read_process_stdout)
        thread.start()

    def _read_process_stdout(self):
        while(self._refresh_running):
            try:
                line = self.process.stdout.readline()
            except ValueError:
                self.Destroy()
                break

            if line is not None:
                line = line.strip()

            if line.startswith("event id "):
                try:
                    event_id = int(line[9:])
                except ValueError:
                    continue

                if event_id == AbstractTaskBarIcon.TASK_BAR_EXIT:
                    self.Destroy()

                self.trigger_event(event_id)
            else:
                _logger.error(line)

    def _refresh_container_list(self):
        self.trigger_refresh_container_list()

        if self._refresh_running and self._is_connected:
            timer = Timer(CONTAINER_STATUS_REFRESH_DELAY,
                          self._refresh_container_list)
            timer.start()

    def set_state(self, state):
        self._send_object(UnityDataExchange(state=state))

        previous_state = self._is_connected
        self._is_connected = state is not AbstractTaskBarIcon.NOT_CONNECTED

        if not previous_state and self._is_connected:
            self._refresh_container_list()

    def set_container_status_list(self, status_list):
        self._send_object(UnityDataExchange(status_list=status_list))

    def _send_object(self, obj):
        if not self.process.stdin.closed:
            obj_string = pickle.dumps(obj)
            self.process.stdin.write("object size %s\n" % len(obj_string))
            self.process.stdin.write(obj_string)
            self.process.stdin.flush()

    def Destroy(self):
        self._refresh_running = False
        self.process.stdin.close()
        self.process.stdout.close()

    def notify_lang_change(self):
        lang = get_lang()
        if lang is not None:
            self._send_object(UnityDataExchange(lang=lang))


def main():
    import wx

    logging.basicConfig()

    app = wx.App()
    task_bar = None

    def exit(_):
        print("exit wx mainloop")
        app.ExitMainLoop()

    def open_win(event):
        print("open win: %s" % event.target)

    def container_status(_):
        print("get container status")

        container_list = [
            ('tmp', '/tmp', AbstractTaskBarIcon.SYNC_DONE),
            ('MyBajoo', '/etc', AbstractTaskBarIcon.SYNC_PROGRESS)]

        task_bar.set_container_status_list(container_list)

    app.Bind(AbstractTaskBarIconWxInterface.EVT_OPEN_WINDOW, open_win)
    app.Bind(AbstractTaskBarIconWxInterface.EVT_EXIT, exit)
    app.Bind(AbstractTaskBarIconWxInterface.EVT_CONTAINER_STATUS_REQUEST,
             container_status)

    task_bar = UnityTaskBarIconWxInterface(app)
    task_bar.set_state(AbstractTaskBarIcon.SYNC_DONE)
    wx.Frame(None)  # wx need at least one object to be alive
    print("start wx main loop")
    app.MainLoop()
    print("wx main loop exited")


if __name__ == '__main__':
    main()
