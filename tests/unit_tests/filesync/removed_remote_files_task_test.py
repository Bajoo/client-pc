#!/usr/bin/env python
# -*- coding: utf-8 -*-


from bajoo.filesync.removed_remote_files_task import RemovedRemoteFilesTask
from bajoo.filesync.task_consumer import start, stop
from bajoo.index.hints import ModifiedHint
from .utils import FakeFile, TestTaskAbstract

import os


def setup_module(module):
    start()


def teardown_module(module):
    stop()


def generate_task(tester, target):
    tester.local_container.inject_empty_node(target)
    return RemovedRemoteFilesTask(tester.container, (target,),
                                  tester.local_container)


class Test_file_does_not_exist(TestTaskAbstract):

    def test_case(self):
        path = "toto"

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        self.check_action()  # no action
        self.assert_conflict(count=0)
        self.assert_not_in_index(path)


class Test_file_exists(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)
        self.file = FakeFile()
        self.add_file_to_close(self.file)

    def test_local_file_is_still_the_same(self):
        assert os.path.exists(self.file.descr.name)

        self.local_container.inject_hash(self.file.filename,
                                         local_hash=self.file.local_hash,
                                         remote_hash=self.file.remote_hash)

        self.execute_task(generate_task(self, self.file.filename))
        self.assert_no_error_on_task()
        assert not os.path.exists(self.file.descr.name)
        self.check_action()  # no action

        self.assert_not_in_index(self.file.filename)

    def test_no_hash(self):
        self.local_container.inject_hash(self.file.filename,
                                         local_hash=None,
                                         remote_hash=None)

        self.execute_task(generate_task(self, self.file.filename))
        self.assert_no_error_on_task()
        self.check_action()

        self.assert_node_has_hint(self.file.filename, local_hint=ModifiedHint)

    def test_local_file_has_been_updated(self):
        self.local_container.inject_hash(self.file.filename,
                                         local_hash="plop",
                                         remote_hash=self.file.remote_hash)

        self.execute_task(generate_task(self, self.file.filename))
        self.assert_no_error_on_task()
        self.check_action()

        self.assert_node_has_hint(self.file.filename, local_hint=ModifiedHint)
