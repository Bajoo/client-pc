#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.common.autorun import is_autorun, set_autorun, can_autorun

"""### TEST CASES ###
    enable autorun, check if enabled
    disable autorun, check if enabled
    multiple enable
    multiple disable
"""

already_enabled = False


def setup_module(module):
    global already_enabled

    already_enabled = is_autorun()


def teardown_module(module):
    global already_enabled

    if already_enabled:
        set_autorun(True)


class TestAutorun(object):

    def testEnable(self):
        if not can_autorun():
            return

        set_autorun(True)
        assert is_autorun()

    def testDisable(self):
        if not can_autorun():
            return

        set_autorun(True)
        assert is_autorun()

        set_autorun(False)
        assert not is_autorun()

    def testMultipleEnable(self):
        if not can_autorun():
            return

        set_autorun(True)
        set_autorun(True)
        set_autorun(True)
        assert is_autorun()

    def testMultipleDisable(self):
        if not can_autorun():
            return

        set_autorun(True)
        assert is_autorun()

        set_autorun(False)
        set_autorun(False)
        set_autorun(False)
        assert not is_autorun()
