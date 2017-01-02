#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.added_local_files_task import AddedLocalFilesTask
from bajoo.filesync.moved_local_files_task import MovedLocalFilesTask
from bajoo.filesync.task_consumer import start, stop
from bajoo.index.hints import DeletedHint, ModifiedHint
from .utils import TestTaskAbstract, generate_random_string, FakeFile

import os
import tempfile


def setup_module(module):
    start()


def teardown_module(module):
    stop()


def generate_task(tester, src_target, dst_target):
    tester.local_container.inject_empty_node(src_target)
    tester.local_container.inject_empty_node(dst_target)
    return MovedLocalFilesTask(
        tester.container,
        (src_target,
         dst_target,
         ),
        tester.local_container)


class FakeMovedLocalFilesTask(MovedLocalFilesTask):

    def _create_push_task(self, rel_path):
        self.local_container.inject_empty_node(rel_path)
        return AddedLocalFilesTask(self.container,
                                   (generate_random_string(),),
                                   self.local_container)


def generate_fake_task(tester, src_target, dst_target):
    tester.local_container.inject_empty_node(src_target)
    tester.local_container.inject_empty_node(dst_target)
    return FakeMovedLocalFilesTask(
        tester.container,
        (src_target,
         dst_target,
         ),
        tester.error_append)


class Test_special_case(TestTaskAbstract):

    def test_SRC_file_exist_BUT_no_dest_file(self):
        src_file = FakeFile()
        self.add_file_to_close(src_file)

        self.local_container.inject_hash(path=src_file.filename,
                                         local_hash="plop",
                                         remote_hash=src_file.remote_hash)

        self.execute_task(generate_task(self, src_file.filename, "plop"))

        self.assert_no_error_on_task()
        self.check_action()
        self.assert_conflict(count=0)

        self.assert_node_has_hint(src_file.filename, local_hint=ModifiedHint)

    def test_SRC_file_exist_AND_dest_file_exists(self):
        src_file = FakeFile()
        self.add_file_to_close(src_file)

        self.local_container.inject_hash(path=src_file.filename,
                                         local_hash="plop",
                                         remote_hash=src_file.remote_hash)

        dest_file = FakeFile()
        self.add_file_to_close(dest_file)

        self.local_container.inject_hash(path=dest_file.filename,
                                         local_hash="plip",
                                         remote_hash=dest_file.remote_hash)

        self.execute_task(
            generate_task(
                self,
                src_file.filename,
                dest_file.filename))
        self.assert_no_error_on_task()

        self.check_action()
        self.assert_conflict(count=0)

        self.assert_node_has_hint(src_file.filename, local_hint=ModifiedHint)
        self.assert_node_has_hint(dest_file.filename, local_hint=ModifiedHint)

    def test_no_file_exists(self):
        self.local_container.inject_hash(path="source",
                                         local_hash="plop",
                                         remote_hash="remote plop")

        self.local_container.inject_hash(path="dest",
                                         local_hash="plip",
                                         remote_hash="remote plip")

        self.container.inject_remote(path="source",
                                     remote_hash="remote plop",
                                     remote_content="fesdrtgfyju")

        self.container.inject_remote(path="dest",
                                     remote_hash="remote plip",
                                     remote_content="desfrgthj")

        self.execute_task(generate_task(self, "source", "dest"))
        self.assert_no_error_on_task()
        self.check_action()
        self.assert_conflict(count=0)

        self.assert_node_has_hint('source', remote_hint=DeletedHint)
        self.assert_node_has_hint('dest', remote_hint=DeletedHint)


class Test_SRC_no_remote_hash_AND_no_remote_file(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.local_container.inject_hash(path=self.origin_path,
                                         local_hash=None,
                                         remote_hash=None)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(
            generate_task(
                self,
                self.origin_path,
                self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename, )
        ulist = (self.destination_file.filename, )
        self.check_action(uploaded=ulist, downloaded=dlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename, )
        self.check_action(downloaded=dlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename
        )
        self.check_action(downloaded=dlist)
        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        ulist = (self.destination_file.filename,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self, self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename
        )
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)
        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)


class Test_SRC_no_remote_hash_AND_remote_not_equal_AND_local_dest_not_equal(
        TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.local_container.inject_hash(path=self.origin_path,
                                         local_hash=None,
                                         remote_hash=None)

        self.remote_src_file = FakeFile()
        self.add_file_to_close(self.remote_src_file)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        ulist = (self.destination_file.filename, )
        self.check_action(downloaded=dlist, uploaded=ulist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        self.check_action(downloaded=dlist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename,
        )
        self.check_action(downloaded=dlist)
        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        ulist = (self.destination_file.filename,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename,
        )
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)
        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)


class Test_SRC_remote_hash_AND_no_remote_file(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.origin_remote_hash = generate_random_string(16)
        self.local_container.inject_hash(path=self.origin_path,
                                         local_hash=self.origin_local_hash,
                                         remote_hash=self.origin_remote_hash)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.destination_file.filename,)
        ulist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.destination_file.filename, )
        glist = (self.origin_path, )
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)
        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        ulist = (self.destination_file.filename, )
        glist = (self.origin_path, self.destination_file.filename)
        self.check_action(uploaded=ulist, getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        glist = (self.origin_path, self.destination_file.filename)
        self.check_action(getinfo=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)


class Test_SRC_remote_hash_AND_equal(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.remote_src_file = FakeFile()
        self.add_file_to_close(self.remote_src_file)
        self.local_container.inject_hash(
            path=self.origin_path,
            local_hash=self.remote_src_file.local_hash,
            remote_hash=self.remote_src_file.remote_hash)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=dlist,
            getinfo=glist,
            removed=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, getinfo=glist, removed=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            getinfo=glist,
            removed=rlist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)
        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        ulist = (self.destination_file.filename, )
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(uploaded=ulist, getinfo=glist, removed=rlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(getinfo=glist, removed=rlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (self.destination_file.filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            getinfo=glist,
            removed=rlist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)


class Test_SRC_remote_hash_AND_not_equal_AND_local_dest_equal(
        TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

        self.local_container.inject_hash(
            path=self.origin_path,
            local_hash=self.destination_file.local_hash,
            remote_hash=generate_random_string(16))

        self.remote_src_file = FakeFile()
        self.add_file_to_close(self.remote_src_file)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        ulist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.remote_src_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, getinfo=glist, removed=glist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.remote_src_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename)
        glist = (self.origin_path,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            getinfo=glist,
            removed=rlist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)
        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, )
        ulist = (self.destination_file.filename, )
        glist = (self.origin_path, self.destination_file.filename, )
        rlist = (self.origin_path, )
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.remote_src_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        ulist = (self.destination_file.filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.remote_src_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename)
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            getinfo=glist,
            removed=rlist)
        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_not_in_index(self.origin_path)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)


class Test_SRC_remote_hash_AND_not_equal_AND_local_dest_not_equal(
        TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.local_container.inject_hash(
            path=self.origin_path,
            local_hash=self.origin_local_hash,
            remote_hash=generate_random_string(16))

        self.remote_src_file = FakeFile()
        self.add_file_to_close(self.remote_src_file)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename)
        ulist = (self.destination_file.filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename, )
        glist = (self.origin_path, )
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=None,
            remote_hash=None)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, getinfo=glist)
        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)

    def test_DEST_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, )
        ulist = (self.destination_file.filename, )
        glist = (self.origin_path, self.destination_file.filename, )
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_remote_hash_AND_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=self.destination_file.remote_hash,
            remote_content=self.destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path,)
        glist = (self.origin_path, self.destination_file.filename, )
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  self.destination_file.local_hash,
                                  self.destination_file.remote_hash)

    def test_DEST_remote_hash_AND_not_equal(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=self.destination_file.remote_hash)

        remote_destination_file = FakeFile()
        self.add_file_to_close(remote_destination_file)

        self.container.inject_remote(
            path=self.destination_file.filename,
            remote_hash=remote_destination_file.remote_hash,
            remote_content=remote_destination_file.descr)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=1)
        conflict_filename = self.conflict_list[0]
        assert conflict_filename.startswith(self.destination_file.filename)

        dlist = (
            self.origin_path,
            self.destination_file.filename)
        glist = (self.origin_path, self.destination_file.filename,)
        self.check_action(downloaded=dlist, getinfo=glist)

        self.assert_node_has_hint(conflict_filename, local_hint=ModifiedHint)

        self.assert_hash_in_index(self.origin_path,
                                  self.remote_src_file.local_hash,
                                  self.remote_src_file.remote_hash)

        self.assert_hash_in_index(self.destination_file.filename,
                                  remote_destination_file.local_hash,
                                  remote_destination_file.remote_hash)
