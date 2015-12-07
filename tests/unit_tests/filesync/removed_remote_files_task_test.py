#!/usr/bin/env python
# -*- coding: utf-8 -*-


from bajoo.filesync.removed_remote_files_task import RemovedRemoteFilesTask
from .utils import FakeFile, TestTaskAbstract

import os


def generate_task(tester, target):
    return RemovedRemoteFilesTask(tester.container, (target,),
                                  tester.local_container,
                                  tester.error_append, None)


class Test_file_does_not_exist(TestTaskAbstract):

    def test_case(self):
        path = "toto"

        self.execute_task(generate_task(self, path))
        self.assert_no_error_on_task()
        self.check_action()  # no action
        self.assert_conflict(count=0)
        assert path in self.local_container.updated_index_but_not_in_dict


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

        assert self.file.filename in \
            self.local_container.updated_index_but_not_in_dict

    def test_no_local_hash(self):
        self.local_container.inject_hash(self.file.filename,
                                         local_hash=None,
                                         remote_hash=self.file.remote_hash)

        self.execute_task(generate_task(self, self.file.filename))
        self.assert_no_error_on_task()
        flist = (self.file.filename, )
        self.check_action(uploaded=flist, getinfo=flist)

        self.assert_index_on_release(self.file.filename,
                                     self.file.local_hash,
                                     self.file.filename + "HASH_UPLOADED")

    def test_local_file_has_been_updated(self):
        self.local_container.inject_hash(self.file.filename,
                                         local_hash="plop",
                                         remote_hash=self.file.remote_hash)

        self.execute_task(generate_task(self, self.file.filename))
        self.assert_no_error_on_task()
        flist = (self.file.filename, )
        self.check_action(uploaded=flist, getinfo=flist)

        self.assert_index_on_release(self.file.filename,
                                     self.file.local_hash,
                                     self.file.filename + "HASH_UPLOADED")
