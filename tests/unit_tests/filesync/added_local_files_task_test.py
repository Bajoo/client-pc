#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.added_local_files_task import AddedLocalFilesTask
from bajoo.filesync.task_consumer import start, stop
from .utils import TestTaskAbstract, generate_random_string, assert_content, \
    FakeFile

import os
import tempfile


def setup_module(module):
    start()


def teardown_module(module):
    stop()


def generate_task(tester, target):
    tester.local_container.inject_empty_node(target)
    return AddedLocalFilesTask(
        tester.container,
        (target,),
        tester.local_container)


class Test_Local_file_does_not_exist(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)
        self.path = generate_random_string()
        self.add_conflict_seed(self.path)

    def test_CreationMode(self):
        self.execute_task(generate_task(self, self.path))
        self.assert_no_error_on_task()
        self.check_action(downloaded=(self.path,))  # no action
        self.assert_conflict(count=0)
        self.assert_not_in_index(self.path)

    def test_UpdateMode(self):
        self.execute_task(generate_task(self, target=self.path))

        self.check_action(downloaded=(self.path,))  # no action
        self.assert_conflict(count=0)
        self.assert_not_in_index(self.path)


class Test_Local_file_exists(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)
        self.local_file = FakeFile()
        self.add_file_to_close(self.local_file)

    def test_RemoteHashAvailableButFileDoesNotExistOnServer(self):
        self.local_container.inject_hash(
            self.local_file.filename,
            local_hash="plop",
            remote_hash=self.local_file.remote_hash)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        flist = (self.local_file.filename,)
        self.check_action(getinfo=flist, uploaded=flist)
        self.assert_conflict(count=0)

        self.assert_hash_in_index(
            self.local_file.filename,
            self.local_file.local_hash,
            self.local_file.filename +
            "HASH_UPLOADED")

    def test_RemoteHashAvailableAndFileStillTheSameOnServer(self):
        self.local_container.inject_hash(
            path=self.local_file.filename,
            local_hash="plop",
            remote_hash=self.local_file.remote_hash)

        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash=self.local_file.remote_hash,
                                     remote_content=self.local_file.descr)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        flist = (self.local_file.filename,)
        self.check_action(getinfo=flist, uploaded=flist)
        self.assert_conflict(count=0)

        self.assert_hash_in_index(
            self.local_file.filename,
            self.local_file.local_hash,
            self.local_file.filename +
            "HASH_UPLOADED")

    def test_RemoteHashDifferentOnServer(self):
        self.local_container.inject_hash(
            path=self.local_file.filename,
            local_hash="toto",
            remote_hash=self.local_file.remote_hash)

        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash="plop",
                                     remote_content=self.local_file.descr)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        flist = (self.local_file.filename,)
        self.check_action(downloaded=flist, getinfo=flist)
        self.assert_conflict(count=0)

        self.assert_hash_in_index(self.local_file.filename,
                                  self.local_file.local_hash,
                                  "plop")

    def test_NoHashAvailableAndFileDoesNotExistOnServer(self):
        self.local_container.inject_hash(path=self.local_file.filename,
                                         local_hash=None,
                                         remote_hash=None)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        flist = (self.local_file.filename,)
        self.check_action(downloaded=flist, uploaded=flist)
        self.assert_conflict(count=0)

        self.assert_hash_in_index(
            self.local_file.filename,
            self.local_file.local_hash,
            self.local_file.filename +
            "HASH_UPLOADED")

    def test_NoHashAvailableAndFileExistsOnServerAndEqual(self):
        self.local_container.inject_hash(path=self.local_file.filename,
                                         local_hash=None,
                                         remote_hash=None)

        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash=self.local_file.remote_hash,
                                     remote_content=self.local_file.descr)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        downloaded = (self.local_file.filename,)
        self.check_action(downloaded=downloaded)
        self.assert_conflict(count=0)

        self.assert_hash_in_index(self.local_file.filename,
                                  self.local_file.local_hash,
                                  self.local_file.remote_hash)


class Test_Conflict(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)
        self.local_file = FakeFile()
        self.add_file_to_close(self.local_file)

    def test_FileExistsAndIsDifferentOnServer(self):
        self.local_container.inject_hash(
            path=self.local_file.filename,
            local_hash="toto",
            remote_hash=self.local_file.remote_hash)

        remote_file = FakeFile()
        self.add_file_to_close(remote_file)

        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash=remote_file.remote_hash,
                                     remote_content=remote_file.descr)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]

        downloaded = (self.local_file.filename,)
        getinfo = (self.local_file.filename, )
        self.check_action(downloaded=downloaded,
                          getinfo=getinfo)
        self.assert_node_exists_and_file_exists(conflict_filename)

        self.assert_hash_in_index(self.local_file.filename,
                                  remote_file.local_hash,
                                  remote_file.remote_hash)

        conflict_path = os.path.join(tempfile.gettempdir(), conflict_filename)
        assert_content(conflict_path, self.local_file.local_hash)
        assert_content(self.local_file.descr.name, remote_file.local_hash)

    def test_NoHashAvailableAndFileExistsOnServerAndNotEqual(self):
        self.local_container.inject_hash(path=self.local_file.filename,
                                         local_hash=None,
                                         remote_hash=None)

        remote_file = FakeFile()
        self.add_file_to_close(remote_file)

        self.container.inject_remote(path=self.local_file.filename,
                                     remote_hash=remote_file.remote_hash,
                                     remote_content=remote_file.descr)

        self.execute_task(generate_task(self, target=self.local_file.filename))
        self.assert_no_error_on_task()

        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]

        downloaded = (self.local_file.filename,)
        self.check_action(downloaded=downloaded)

        self.assert_node_exists_and_file_exists(conflict_filename)

        self.assert_hash_in_index(self.local_file.filename,
                                  remote_file.local_hash,
                                  remote_file.remote_hash)

        conflict_path = os.path.join(tempfile.gettempdir(), conflict_filename)
        assert_content(conflict_path, self.local_file.local_hash)
        assert_content(self.local_file.descr.name, remote_file.local_hash)
