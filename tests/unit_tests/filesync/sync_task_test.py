#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.filesync.added_local_files_task import AddedLocalFilesTask
from bajoo.filesync.sync_task import SyncTask
from .utils import TestTaskAbstract, generate_random_string, FakeFile

from tempfile import mkdtemp
import os


class FakeSyncTask(SyncTask,):
    def _create_push_task(self, rel_path, ignore_missing_file=False):
        return AddedLocalFilesTask(self.container,
                                   (generate_random_string(),),
                                   self.local_container,
                                   self.display_error_cb,
                                   parent_path=self._parent_path,
                                   ignore_missing_file=ignore_missing_file)


def generate_fake_task(tester, target, ignore_missing_file=False):
    return FakeSyncTask(
        tester.container,
        (target,),
        tester.local_container,
        tester.error_append,
        None,
        ignore_missing_file)


class TestSyncTask(TestTaskAbstract):
    def test_crash_several_sub_task(self):
        tempDirPath = mkdtemp()
        tempDirPathInTmp = os.path.split(tempDirPath)[1]
        self.add_file_to_remove(tempDirPath)

        fake_file = FakeFile(dir=tempDirPath)
        self.add_file_to_close(fake_file)
        path_in_container = os.path.join(tempDirPathInTmp, fake_file.filename)
        self.local_container.inject_hash(path_in_container, "local", "remote")

        fake_file = FakeFile(dir=tempDirPath)
        self.add_file_to_close(fake_file)
        path_in_container = os.path.join(tempDirPathInTmp, fake_file.filename)
        self.local_container.inject_hash(path_in_container, "local", "remote")

        fake_file = FakeFile(dir=tempDirPath)
        self.add_file_to_close(fake_file)
        path_in_container = os.path.join(tempDirPathInTmp, fake_file.filename)
        self.local_container.inject_hash(path_in_container, "local", "remote")

        self.execute_task(generate_fake_task(self, tempDirPathInTmp))

        assert self.result is not None
        assert len(self.result) == 3
        assert len(set(self.result)) == 3

        assert isinstance(self.result[0], AddedLocalFilesTask)
        assert isinstance(self.result[1], AddedLocalFilesTask)
        assert isinstance(self.result[2], AddedLocalFilesTask)

# TODO test the remaining stuff in the class SyncTask
