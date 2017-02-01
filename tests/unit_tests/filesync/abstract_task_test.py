#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.abstract_task import _Task
from .utils import TestTaskAbstract


class FakeTask(_Task):
    @staticmethod
    def get_type():
        return "fake"

    def _apply_task(self):
        target = self.nodes[0]
        target.set_hash("local", "remote")
        yield None
        return


def generate_task(tester, target):
    tester.local_container.inject_empty_node(target)
    return FakeTask(tester.container, (target,),
                    tester.local_container)


class TestAbstractTaskTargetEncoding(TestTaskAbstract):
    def test_unicode_case(self):
        task = generate_task(self, u"plop")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_hash_in_index("plop", "local", "remote")

    def test_unicode_special_case(self):
        task = generate_task(self, u"plôp")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_hash_in_index(u"plôp", "local", "remote")

    def test_unicode_ultra_special_case(self):
        task = generate_task(self, u"pl❤p")
        self.execute_task(task)
        self.assert_no_error_on_task()
        self.assert_hash_in_index(u"pl❤p", "local", "remote")

# TODO test every other methods in abstract_task
