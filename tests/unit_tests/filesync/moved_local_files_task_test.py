#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.moved_local_files_task import MovedLocalFilesTask
from .utils import TestTaskAbstract, generate_random_string, FakeFile

import os
import tempfile


def generate_task(tester, src_target, dst_target):
    return MovedLocalFilesTask(
        tester.container,
        (src_target,
         dst_target,
         ),
        tester.local_container,
        tester.error_append,
        None)


class Test_special_case(TestTaskAbstract):

    def test_SRC_file_exist_BUT_no_dest_file(self):
        src_file = FakeFile()
        self.add_file_to_close(src_file)

        self.local_container.inject_hash(path=src_file.filename,
                                         local_hash="plop",
                                         remote_hash=src_file.remote_hash)

        self.execute_task(generate_task(self, src_file.filename, "plop"))

        self.assert_no_error_on_task()
        flist = (src_file.filename, )
        self.check_action(uploaded=flist, getinfo=flist)
        self.assert_conflict(count=0)

        self.assert_index_on_release(src_file.filename,
                                     src_file.local_hash,
                                     src_file.filename + "HASH_UPLOADED")

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

        flist = (src_file.filename, dest_file.filename)
        self.check_action(uploaded=flist, getinfo=flist)
        self.assert_conflict(count=0)

        self.assert_index_on_release(src_file.filename,
                                     src_file.local_hash,
                                     src_file.filename + "HASH_UPLOADED")

        self.assert_index_on_release(dest_file.filename,
                                     dest_file.local_hash,
                                     dest_file.filename + "HASH_UPLOADED")

    def test_DEST_file_does_not_exist(self):
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
        flist = ("source", "dest", )
        self.check_action(removed=flist, getinfo=flist)
        self.assert_conflict(count=0)

        assert len(self.local_container.updated_index_but_not_in_dict) == 2
        assert "source" in self.local_container.updated_index_but_not_in_dict
        assert "dest" in self.local_container.updated_index_but_not_in_dict


class Test_SRC_no_remote_hash_AND_no_remote_file(TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.local_container.inject_hash(path=self.origin_path,
                                         local_hash=self.origin_local_hash,
                                         remote_hash=None)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        self.check_action(downloaded=dlist, uploaded=ulist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2
        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2
        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


class Test_SRC_no_remote_hash_AND_remote_equal_file(TestTaskAbstract):

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
            remote_hash=None)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

        self.destination_file = FakeFile()
        self.add_file_to_close(self.destination_file)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        ulist = (self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, getinfo=glist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
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
            conflict_filename,
        )
        ulist = (conflict_filename, )
        glist = (self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


class Test_SRC_no_remote_hash_AND_remote_not_equal_file_AND_local_dest_equal(
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
            remote_hash=None)

        self.remote_src_file = FakeFile()
        self.add_file_to_close(self.remote_src_file)

        self.container.inject_remote(
            path=self.origin_path,
            remote_hash=self.remote_src_file.remote_hash,
            remote_content=self.remote_src_file.descr)

    def test_DEST_no_remote_hash_AND_no_remote_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        ulist = (self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.remote_src_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.remote_src_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        rlist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.remote_src_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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
        glist = (self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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
            self.destination_file.filename,
            conflict_filename,
        )
        ulist = (conflict_filename,)
        glist = (self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.remote_src_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


class Test_SRC_no_remote_hash_AND_remote_not_equal_AND_local_dest_not_equal(
        TestTaskAbstract):

    def setup_method(self, method):
        TestTaskAbstract.setup_method(self, method)

        self.origin_path = generate_random_string(20)
        origin_path = os.path.join(tempfile.gettempdir(), self.origin_path)
        self.add_file_to_remove(origin_path)

        self.origin_local_hash = generate_random_string(16)
        self.local_container.inject_hash(path=self.origin_path,
                                         local_hash=self.origin_local_hash,
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
            local_hash=self.destination_file.local_hash,
            remote_hash=None)

        self.execute_task(generate_task(self,
                                        self.origin_path,
                                        self.destination_file.filename))

        self.assert_no_error_on_task()
        self.assert_conflict(count=0)

        dlist = (self.origin_path, self.destination_file.filename,)
        ulist = (self.destination_file.filename, )
        self.check_action(downloaded=dlist, uploaded=ulist)

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        self.check_action(downloaded=dlist, uploaded=ulist)

        assert len(self.local_container.index_on_release) == 3

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(
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

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        glist = (self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.index_on_release) == 3

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


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
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        dlist = (self.destination_file.filename, conflict_filename)
        ulist = (conflict_filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
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

        dlist = (self.destination_file.filename, conflict_filename,)
        ulist = (conflict_filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


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
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        dlist = (self.destination_file.filename, conflict_filename,)
        ulist = (conflict_filename,)
        glist = (self.origin_path,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
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

        dlist = (self.destination_file.filename, conflict_filename,)
        ulist = (conflict_filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


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
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
            self.destination_file.filename,
            self.remote_src_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(self.destination_file.filename,
                                     self.remote_src_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename)
        ulist = (conflict_filename,)
        glist = (self.origin_path,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.remote_src_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 1
        self.assert_index_on_release(
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
            self.destination_file.filename,
            conflict_filename,
        )
        ulist = (conflict_filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        rlist = (self.origin_path,)
        self.check_action(
            downloaded=dlist,
            uploaded=ulist,
            getinfo=glist,
            removed=rlist)

        assert len(self.local_container.updated_index_but_not_in_dict) == 1
        assert self.origin_path in \
            self.local_container.updated_index_but_not_in_dict

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.remote_src_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")


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
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(
            self.destination_file.filename,
            self.destination_file.local_hash,
            self.destination_file.filename + "HASH_UPLOADED")

    def test_DEST_no_remote_hash_AND_remote_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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

        assert len(self.local_container.index_on_release) == 2

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     self.destination_file.local_hash,
                                     self.destination_file.remote_hash)

    def test_DEST_no_remote_hash_AND_remote_not_equal_file(self):
        self.local_container.inject_hash(
            path=self.destination_file.filename,
            local_hash=self.destination_file.local_hash,
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
            conflict_filename,
        )
        ulist = (conflict_filename,)
        glist = (self.origin_path,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.index_on_release) == 3

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")

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

        assert len(self.local_container.index_on_release) == 2
        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(
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

        assert len(self.local_container.index_on_release) == 2
        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
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
            conflict_filename)
        ulist = (conflict_filename,)
        glist = (self.origin_path, self.destination_file.filename,)
        self.check_action(downloaded=dlist, uploaded=ulist, getinfo=glist)

        assert len(self.local_container.index_on_release) == 3

        self.assert_index_on_release(self.origin_path,
                                     self.remote_src_file.local_hash,
                                     self.remote_src_file.remote_hash)

        self.assert_index_on_release(self.destination_file.filename,
                                     remote_destination_file.local_hash,
                                     remote_destination_file.remote_hash)

        self.assert_index_on_release(conflict_filename,
                                     self.destination_file.local_hash,
                                     conflict_filename + "HASH_UPLOADED")
