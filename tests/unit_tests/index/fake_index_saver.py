# -*- coding: utf-8 -*-


class FakeIndexSaver(object):

    def __init__(self):
        self.triggered = 0

    def trigger_save(self):
        self.triggered += 1
