#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.abstract_task import _Task
from .utils import TestTaskAbstract


class FakeTask(_Task):
    @staticmethod
    def get_type():
        return "fake"

    def _apply_task(self):
        target = self.target_list[0]

        yield {target.rel_path: ("local", "remote")}
        return


def generate_task(tester, target):
    return FakeTask(tester.container, (target,),
                    tester.local_container,
                    tester.error_append, None)


class TestAbstractTaskTargetEncoding(TestTaskAbstract):
    def test_unicode_case(self):
        task = generate_task(self, u"plop")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_index_on_release("plop", "local", "remote")

    def test_unicode_special_case(self):
        task = generate_task(self, u"plôp")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_index_on_release(u"plôp", "local", "remote")

    def test_unicode_ultra_special_case(self):
        task = generate_task(self, u"pl❤p")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_index_on_release(u"pl❤p", "local", "remote")

# TODO test every other methods in abstract_task