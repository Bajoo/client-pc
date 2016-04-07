# -*- coding: utf-8 -*-


class FakeTask(object):

    def __init__(self):
        self.callback_called = False
        self.cancel = None
        self.release_aquired_lock = None

    def callback(self, cancel=False, release_aquired_lock=True):
        self.callback_called = True
        self.cancel = cancel
        self.release_aquired_lock = release_aquired_lock
