#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile

from bajoo.filesync.removed_local_files_task import RemovedLocalFilesTask
from bajoo.filesync.task_consumer import start, stop
from bajoo.index.hints import ModifiedHint
from .utils import FakeFile, TestTaskAbstract


def setup_module(module):
    start()


def teardown_module(module):
    stop()


def generate_task(tester, target):
    tester.local_container.inject_empty_node(target)

    return RemovedLocalFilesTask(tester.container, (target,),
                                 tester.local_container)


class Test_Removed_local_files_task(TestTaskAbstract):

    def test_file_exists(self):
        f = FakeFile()
        self.add_file_to_close(f)

        self.execute_task(generate_task(self, f.filename))
        self.assert_no_error_on_task()
        self.check_action()  # no action
        self.assert_conflict(count=0)

        # Will start another local add task.
        self.assert_node_has_hint(f.filename, local_hint=ModifiedHint)

    def test_remote_hash_not_available(self):
        path = "toto"
        self.add_conflict_seed(path)

        self.local_container.inject_hash(path=path,
                                         local_hash=None,
                                         remote_hash=None)

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        self.check_action()  # no action
        self.assert_conflict(count=0)
        self.assert_node_has_hint(path, remote_hint=ModifiedHint)

        # check md5 update
        self.assert_not_in_index(path)

    def test_no_file_on_server(self):
        path = "toto"
        self.add_conflict_seed(path)

        self.local_container.inject_hash(path=path,
                                         local_hash="titi",
                                         remote_hash="REMOTE HASH")

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        self.check_action(getinfo=(path,))
        self.assert_conflict(count=0)
        self.assert_not_in_index(path)

    def test_file_on_server_is_equal(self):
        path = "toto"
        self.add_conflict_seed(path)

        self.local_container.inject_hash(path=path,
                                         local_hash="titi",
                                         remote_hash="REMOTE HASH")

        self.container.inject_remote(path=path,
                                     remote_hash="REMOTE HASH",
                                     remote_content="titi")

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        flist = (path,)
        self.check_action(getinfo=flist, removed=flist)
        self.assert_conflict(count=0)
        self.assert_not_in_index(path)

    def test_file_on_server_is_different(self):
        f = FakeFile()
        self.add_file_to_close(f)

        path = "toto"
        self.add_conflict_seed(path)

        self.add_file_to_remove(os.path.join(tempfile.gettempdir(),
                                             path))

        self.local_container.inject_hash(path=path,
                                         local_hash="titi",
                                         remote_hash="REMOTE HASH")

        self.container.inject_remote(path=path,
                                     remote_hash="DIFFERENT REMOTE HASH",
                                     remote_content=f.descr)

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        self.check_action(getinfo=(path,))
        self.assert_conflict(count=0)
        self.assert_node_has_hint(path, remote_hint=ModifiedHint)
