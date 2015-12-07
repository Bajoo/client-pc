#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.added_remote_files_task import AddedRemoteFilesTask
from .utils import FakeFile, TestTaskAbstract, assert_content

import os
import tempfile


def generate_task(tester, target):
    return AddedRemoteFilesTask(
        tester.container,
        (target,
         ),
        tester.local_container,
        tester.error_append,
        None)


class Test_Remote_File_does_not_exist(TestTaskAbstract):

    def test_case(self):
        path = "plop"
        self.add_conflict_seed(path)

        self.execute_task(generate_task(self, path))

        self.assert_no_error_on_task()
        self.check_action(downloaded=(path,))
        self.assert_conflict(count=0)

        # check md5 update
        assert path in self.local_container.updated_index_but_not_in_dict


class Test_Remote_File_exists_but_not_local(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.remote_file = FakeFile()
        self.add_file_to_close(self.remote_file)

        self.local_path = "toto"
        self.add_conflict_seed(self.local_path)
        local_absolute_path = os.path.join(tempfile.gettempdir(),
                                           self.local_path)
        self.add_file_to_remove(local_absolute_path)

    def test_file_does_not_exist_locally(self):
        self.container.inject_remote(path=self.local_path,
                                     remote_hash=self.remote_file.remote_hash,
                                     remote_content=self.remote_file.descr)

        self.execute_task(generate_task(self, self.local_path))

        self.assert_no_error_on_task()
        self.check_action(downloaded=(self.local_path,))
        self.assert_conflict(count=0)
        self.assert_index_on_release(self.local_path,
                                     self.remote_file.local_hash,
                                     self.remote_file.remote_hash)


class Test_Remote_and_Local_File_exist(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.remote_file = FakeFile()
        self.add_file_to_close(self.remote_file)
        self.local_file = FakeFile("")  # empty local file
        self.add_file_to_close(self.local_file)

    def registerFiles(self, localRegistration=True):
        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash=self.remote_file.remote_hash,
                                     remote_content=self.remote_file.descr)

        if localRegistration:
            self.local_container.inject_hash(
                path=self.local_file.filename,
                local_hash=self.local_file.local_hash,
                remote_hash=self.remote_file.remote_hash)

    def test_not_registered_locally_but_equal(self):
        self.local_file.writeContent(self.remote_file.content)
        self.registerFiles(localRegistration=False)

        self.execute_task(generate_task(self, self.local_file.filename))

        self.assert_no_error_on_task()
        self.check_action(downloaded=(self.local_file.filename,))
        self.assert_conflict(count=0)
        self.assert_index_on_release(self.local_file.filename,
                                     self.remote_file.local_hash,
                                     self.remote_file.remote_hash)

    def test_not_registered_locally_AND_not_equal(self):
        self.local_file.writeRandom()
        self.registerFiles(localRegistration=False)

        self.execute_task(generate_task(self, self.local_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]

        downloaded = (self.local_file.filename, conflict_filename, )
        uploaded = (conflict_filename, )
        self.check_action(downloaded=downloaded, uploaded=uploaded)

        self.assert_index_on_release(self.local_file.filename,
                                     self.remote_file.local_hash,
                                     self.remote_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.local_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

        assert_content(self.local_file.descr.name, self.remote_file.local_hash)
        conflict_path = os.path.join(tempfile.gettempdir(), conflict_filename)
        assert_content(conflict_path, self.local_file.local_hash)

    def test_registered_locally_but_equal(self):
        self.local_file.writeRandom()
        self.registerFiles(localRegistration=True)

        self.execute_task(generate_task(self, self.local_file.filename))

        self.assert_no_error_on_task()
        self.check_action(downloaded=(self.local_file.filename,))
        self.assert_conflict(count=0)

        self.assert_index_on_release(self.local_file.filename,
                                     self.remote_file.local_hash,
                                     self.remote_file.remote_hash)

    def test_registered_locally_AND_not_equal(self):
        self.registerFiles(localRegistration=True)
        self.local_file.writeRandom()

        self.execute_task(generate_task(self, self.local_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]

        downloaded = (self.local_file.filename, conflict_filename, )
        uploaded = (conflict_filename, )
        self.check_action(downloaded=downloaded, uploaded=uploaded)

        self.assert_index_on_release(self.local_file.filename,
                                     self.remote_file.local_hash,
                                     self.remote_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.local_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

        assert_content(self.local_file.descr.name, self.remote_file.local_hash)
        conflict_path = os.path.join(tempfile.gettempdir(), conflict_filename)
        assert_content(conflict_path, self.local_file.local_hash)
