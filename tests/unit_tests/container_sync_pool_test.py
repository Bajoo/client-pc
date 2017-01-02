#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import threading

import pytest

import bajoo.container_sync_pool as csp
from bajoo.filesync.task_consumer import add_task, start, stop
from bajoo.filesync.added_local_files_task import AddedLocalFilesTask

from .filesync.fake_local_container import FakeLocalContainer
from .filesync.fake_container import Fake_container, \
    FakeHTTPEntityTooLargeError, FakePassphraseAbortError
from .filesync.utils import FakeFile


# backup module before mock
OLD_FILEWATCHER = csp.FileWatcher
OLD_QUOTA_TIMEOUT = csp.ContainerSyncPool.QUOTA_TIMEOUT

OLD_LOGGER_HANDLERS = None


def setup_module(module):
    global OLD_LOGGER_HANDLERS

    # Some tests expect messages from stdout/stderr. the logging module
    # interact with std streams, and logging configuration is modified by
    # these tests.
    # The setup and teardown ensures the logger stays unchanged after tests
    # execution.
    logger = logging.getLogger()
    OLD_LOGGER_HANDLERS = list(logger.handlers)

    start()


def teardown_module(module):
    global OLD_LOGGER_HANDLERS

    logger = logging.getLogger()
    logger.handlers = OLD_LOGGER_HANDLERS
    logger.setLevel(logging.INFO)

    stop()


class FakeFileWatcher(object):
    INSTANCE = []

    def __init__(self, container_model, on_new_files, on_changed_files,
                 on_moved_files, on_deleted_files):
        self._on_new_files = on_new_files
        FakeFileWatcher.INSTANCE.append(self)

    def start(self):
        pass

    def stop(self):
        pass

    def on_moved(self, event):
        pass

    def on_created(self, event):
        self._on_new_files(event.src_path)

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        pass


class FakeEvent(object):

    def __init__(self, src_path):
        self.src_path = src_path


def FakeTask():
    yield None
    return


class FakeFileSyncModule(object):

    def __init__(self):
        self.result = {}

    def reset_result(self):
        self.result.clear()

    def increment(self, key):
        if key in self.result:
            self.result[key] += 1
        else:
            self.result[key] = 1

    def assertTaskCreation(self, **expected_tasks):
        local_result = self.result.copy()
        for task_name, task_count in expected_tasks.items():
            assert ((task_name not in local_result and task_count == 0) or
                    task_count == local_result[task_name])

            del local_result[task_name]

        for task_name, task_count in local_result.items():
            assert local_result[task_name] == 0

    def added_remote_files(self, *arg, **args):
        self.increment("added_remotly_count")
        return add_task(FakeTask)

    def changed_remote_files(self, *arg, **args):
        self.increment("updated_remotly_count")
        return add_task(FakeTask)

    def removed_remote_files(self, *arg, **args):
        self.increment("removed_remotly_count")
        return add_task(FakeTask)

    def added_local_files(self, container, local_container, filename):

        task = AddedLocalFilesTask(container, (filename,), local_container)
        self.increment("added_locally_count")
        return add_task(task)

    def changed_local_files(self, *arg, **args):
        self.increment("updated_locally_count")
        return add_task(FakeTask)

    def removed_local_files(self, *arg, **args):
        self.increment("removed_locally_count")
        return add_task(FakeTask)

    def moved_local_files(self, *arg, **args):
        self.increment("moved_locally_count")
        return add_task(FakeTask)

    def sync_folder(self, *arg, **args):
        self.increment("sync_task_count")
        return add_task(FakeTask)


@pytest.mark.xfail(
    condition=True, reason="Error produced due to wrongassumptions. See the"
                           "method 'on_container_change_state()' bellow.")
class TestContainerSyncPool(object):

    def on_container_change_state(self, new_state):
        self.state_stack.append(new_state)

        # TODO: This method expects a call to this method after every task
        # resolution (so it assumes one test is finished at each call).
        # It's not the case if several tests are executed simultaneously.
        if new_state is csp.ContainerSyncPool.STATUS_UP_TO_DATE:
            with self.test_condition:
                self.test_finished += 1
                self.test_condition.notify_all()

    def on_container_error(self, error):
        self.error = error

    @classmethod
    def setup_class(cls):
        csp.FileWatcher = FakeFileWatcher
        cls.staticfileSync = FakeFileSyncModule()
        csp.filesync.added_local_files = cls.staticfileSync.added_local_files
        csp.filesync.added_remote_files = cls.staticfileSync.added_remote_files
        csp.filesync.changed_local_files = \
            cls.staticfileSync.changed_local_files
        csp.filesync.changed_remote_files = \
            cls.staticfileSync.changed_remote_files
        csp.filesync.moved_local_files = cls.staticfileSync.moved_local_files
        csp.filesync.removed_local_files = \
            cls.staticfileSync.removed_local_files
        csp.filesync.removed_remote_files = \
            cls.staticfileSync.removed_remote_files
        csp.filesync.sync_folder = cls.staticfileSync.sync_folder
        csp.ContainerSyncPool.QUOTA_TIMEOUT = 0.1

    @classmethod
    def teardown_class(cls):
        csp.FileWatcher = OLD_FILEWATCHER
        csp.ContainerSyncPool.QUOTA_TIMEOUT = OLD_QUOTA_TIMEOUT

    def setup_method(self, method):
        del FakeFileWatcher.INSTANCE[:]

        self.sync_pool = csp.ContainerSyncPool(
            self.on_container_change_state,
            self.on_container_error)

        self.error = None

        self.fake_file = FakeFile()

        self.test_condition = threading.Condition()
        self.test_finished = 0
        self.state_stack = []

        self.lc = FakeLocalContainer(container=Fake_container())
        self.sync_pool.add(self.lc)

        logger = logging.getLogger()
        for h in list(logger.handlers):
            logger.removeHandler(h)

    def teardown_method(self, method):
        self.sync_pool.remove(self.lc)
        self.fake_file.descr.close()
        self.staticfileSync.reset_result()

    def wait_for_task_to_be_executed(self, expected_task=1):
        # wait for execution to be finished
        with self.test_condition:
            # in worst case, wait +- 2.5 seconds, should be enough
            count = 5
            while self.test_finished < expected_task and count > 0:
                self.test_condition.wait(0.5)
                count -= 1

            assert self.test_finished == expected_task

        assert len(self.state_stack) > 1
        assert self.state_stack[-2] is csp.ContainerSyncPool.STATUS_SYNCING
        assert self.state_stack[-1] is csp.ContainerSyncPool.STATUS_UP_TO_DATE

    def trigger_added_local_file(self, src_path):
        assert len(FakeFileWatcher.INSTANCE) == 1
        FakeFileWatcher.INSTANCE[0].on_created(FakeEvent(src_path))

    def test_added_file(self):
        self.trigger_added_local_file(self.fake_file.descr.name)

        self.wait_for_task_to_be_executed(expected_task=2)
        assert self.error is None

        assert self.lc.status_stack == [self.lc.STATUS_STARTED,
                                        self.lc.STATUS_STARTED]

        self.staticfileSync.assertTaskCreation(sync_task_count=1,
                                               added_locally_count=1)

    def test_added_file_with_quota_reached(self):
        quota_exception = FakeHTTPEntityTooLargeError()
        self.lc.container.exception_to_raise_on_upload = quota_exception

        self.trigger_added_local_file(self.fake_file.descr.name)

        self.wait_for_task_to_be_executed(expected_task=3)
        assert str(quota_exception) in self.error
        self.staticfileSync.assertTaskCreation(sync_task_count=2,
                                               added_locally_count=1)

        assert self.lc.status_stack == [
            self.lc.STATUS_STARTED,
            self.lc.STATUS_STARTED,
            self.lc.STATUS_QUOTA_EXCEEDED,
            self.lc.STATUS_STARTED]

        # try to upload again without quota limitation

        self.test_finished = 0
        self.error = None
        del self.state_stack[:]
        del self.lc.status_stack[:]
        self.lc.container.exception_to_raise_on_upload = None

        self.trigger_added_local_file(self.fake_file.descr.name)
        self.wait_for_task_to_be_executed(expected_task=1)

        assert self.error is None
        self.staticfileSync.assertTaskCreation(sync_task_count=2,
                                               added_locally_count=2)
        assert self.lc.status_stack == []

    def test_passphrase_refused(self, capsys):
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

        passphrase_refused = FakePassphraseAbortError()
        self.lc.container.exception_to_raise_on_upload = passphrase_refused

        self.trigger_added_local_file(self.fake_file.descr.name)

        self.wait_for_task_to_be_executed(expected_task=2)
        assert str(passphrase_refused) in self.error
        self.staticfileSync.assertTaskCreation(sync_task_count=1,
                                               added_locally_count=1)

        assert self.lc.status_stack == [
            self.lc.STATUS_STARTED,
            self.lc.STATUS_STARTED,
            self.lc.STATUS_WAIT_PASSPHRASE]

        out, err = capsys.readouterr()
        assert 'Local container is not running, abort task' not in out

        # try to execute another task with local container waiting
        # for the passphrase

        self.test_finished = 0
        self.error = None
        del self.state_stack[:]
        del self.lc.status_stack[:]
        self.lc.container.exception_to_raise_on_upload = None

        self.trigger_added_local_file(self.fake_file.descr.name)
        assert self.error is None
        assert len(self.lc.status_stack) == 0

        out, err = capsys.readouterr()
        assert 'Local container is not running, abort task' in out

# TODO test the other parts of ContainerSyncPool
