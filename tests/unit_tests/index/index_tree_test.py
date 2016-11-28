#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

import bajoo.index.index_tree

from bajoo.index.index_node import DirectoryNode
from bajoo.index.index_tree import IndexTree
from bajoo.index.index_tree import trigger_local_create_task
from bajoo.index.index_tree import trigger_local_delete_task
from bajoo.index.index_tree import trigger_local_moved_task
from bajoo.filesync.added_local_files_task import AddedLocalFilesTask
from bajoo.filesync.added_remote_files_task import AddedRemoteFilesTask
from bajoo.filesync.exception import RedundantTaskInterruption
from bajoo.filesync.moved_local_files_task import MovedLocalFilesTask
from bajoo.filesync.removed_local_files_task import RemovedLocalFilesTask
from bajoo.filesync.removed_remote_files_task import RemovedRemoteFilesTask
from bajoo.promise import Promise

from ..filesync.fake_local_container import FakeLocalContainer
from .fake_index_saver import FakeIndexSaver
from .fake_task import FakeTask
from .fake_directory_node import FakeDirectoryNode

task_added = []
old_add_task = None


def add_task(task, priority=False):
    global task_added
    task_added.append((task, priority,))


def setup_module(module):
    global old_add_task
    old_add_task = bajoo.index.index_tree.add_task
    bajoo.index.index_tree.add_task = add_task


def teardown_module(module):
    global old_add_task
    bajoo.index.index_tree.add_task = old_add_task


class TestException(object):

    def test_raise(self):
        with pytest.raises(RedundantTaskInterruption):
            raise RedundantTaskInterruption()


class TestTriggering(object):

    def setup_method(self, method):
        global task_added
        del task_added[:]

        self.lc = FakeLocalContainer()
        self.previous_task = AddedRemoteFilesTask(container=None,
                                                  target=("aaaa/bbb/ccc",),
                                                  local_container=self.lc)

    def test_trigger_local_create_task(self):
        global task_added

        trigger_local_create_task("aaaa/bbb/ccc", self.previous_task)
        assert len(task_added) == 1
        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, AddedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/ccc"

    def test_trigger_local_delete_task(self):
        global task_added

        trigger_local_delete_task("aaaa/bbb/ccc", self.previous_task)
        assert len(task_added) == 1
        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, RemovedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/ccc"

    def test_trigger_local_moved_task(self):
        global task_added

        trigger_local_moved_task(
            "aaaa/bbb/ccc",
            "aaaa/bbb/cccd",
            self.previous_task)
        assert len(task_added) == 1
        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, MovedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/ccc"
        assert new_task.target_list[1] == "aaaa/bbb/cccd"


def fake_aquire(target_list, task, prior_acquire=False):
    return Promise.resolve({})


class TestIndexTree(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)

    def test_init_with_empty_dict(self):
        tree = IndexTree("saver")
        assert isinstance(tree.root, DirectoryNode)
        assert tree.locked_count == 0
        assert tree.index_saver == "saver"

    def test_init_with_dict(self):
        node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                 create=False)
        assert node is not None

        node = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                 create=False)
        assert node is not None

        node = self.tree.root.get_or_insert_node("aaaa/bbb/hhh",
                                                 create=False)
        assert node is not None

        node = self.tree.root.get_or_insert_node("fff/eee", create=False)
        assert node is not None

        node = self.tree.root.get_or_insert_node("ggg", create=False)
        assert node is not None

    def test_inner_release_file_locked(self):
        task = "task"
        node1 = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                  create=False)
        node1.lock(executing_task=task)

        node2 = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                  create=False)
        node2.lock(executing_task=task)

        self.tree.release(("aaaa/bbb/ccc", "aaaa/bbb/ddd"), task)

        assert not node1.is_locked()
        assert not node2.is_locked()

    def test_inner_release_file_locked_not_owner(self):
        task = "task"
        node1 = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                  create=False)
        node1.lock(executing_task=task)

        node2 = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                  create=False)
        node2.lock("owner", executing_task=task)

        self.tree.release(("aaaa/bbb/ccc", "aaaa/bbb/ddd"), task)

        assert not node1.is_locked()
        assert node2.is_locked()

    def test_inner_release_dir_completly_locked(self):
        task = "task"
        node0 = self.tree.root.get_or_insert_node("aaaa/bbb",
                                                  create=False)
        node0.lock(executing_task=task)

        node0.lock

        node1 = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                  create=False)
        node1.lock(owner=node0)

        node2 = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                  create=False)
        node2.lock(owner=node0)

        self.tree.release(("aaaa/bbb/",), task)

        assert not node0.is_locked()
        assert not node1.is_locked()
        assert not node2.is_locked()

    # TODO not implemented yet
    # def test_inner_release_dir_partialy_locked(self):
    #     pass

    def test_generate_waiting_promise(self):
        task = "task"
        node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                 create=False)

        self.tree.acquire = fake_aquire
        p = self.tree._generate_waiting_promise(
            node, ("aaaa/bbb/ccc", ), task)

        assert node.waiting_task is task
        assert node.waiting_task_callback is not None

        node.waiting_task_callback()

        assert p.result() == {}

    def test_generate_waiting_promise_with_cancel(self):
        task = "task"
        node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                 create=False)

        self.tree.acquire = fake_aquire
        p = self.tree._generate_waiting_promise(
            node, ("aaaa/bbb/ccc", ), task)

        assert node.waiting_task is task
        assert node.waiting_task_callback is not None

        node.waiting_task_callback(cancel=True)

        with pytest.raises(RedundantTaskInterruption):
            p.result()

    def test_steal_sync_task_on_children(self):
        node_bbb = self.tree.root.get_or_insert_node("aaaa/bbb",
                                                     create=False)

        node_ccc = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                     create=False)

        node_ddd = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                     create=False)

        node_fff = self.tree.root.get_or_insert_node("fff",
                                                     create=False)

        node_ccc.lock(owner=node_bbb)
        node_ddd.lock(owner=node_bbb)

        fake_directory_node = FakeDirectoryNode()

        fff_fake_task = FakeTask()
        node_fff.lock(owner=node_fff, executing_task="task")
        node_fff.waiting_task = fff_fake_task
        node_fff.waiting_task_callback = fff_fake_task.callback
        node_fff.waiting_for_node = fake_directory_node

        fake_task = FakeTask()
        node_bbb.waiting_task = fake_task
        node_bbb.waiting_task_callback = fake_task.callback
        node_bbb.waiting_for_node = fake_directory_node

        # put a task waitin on bbb but not locked
        # steal locks

        node = self.tree.root.get_or_insert_node(".", create=False)
        self.tree._steal_sync_task_on_children(node)

        assert fake_task.cancel
        assert node_bbb.waiting_task is None
        assert node_bbb.waiting_task_callback is None
        assert node_bbb.waiting_for_node is None
        assert node_bbb in fake_directory_node.removed_nodes
        assert node_ccc.lock_owner is node
        assert node_ddd.lock_owner is node
        assert node_fff.is_locked()
        assert node_fff.waiting_task is None
        assert node_fff in fake_directory_node.removed_nodes

    def test_lock_children_no_children_locked(self):
        node = self.tree.root.get_or_insert_node(".", create=False)
        assert self.tree._lock_children(node) is None

        for child in node.traverse():
            if child is node:
                continue

            assert child.lock_owner is node

    def test_lock_children_one_locked_children(self):
        node_ccc = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                     create=False)
        node_ccc.lock(self.tree.root)

        node_ddd = self.tree.root.get_or_insert_node("aaaa/bbb/ddd",
                                                     create=False)

        node_ddd.lock(node_ddd, "task")

        assert self.tree._lock_children(self.tree.root) is node_ddd

        for child in self.tree.root.traverse():
            if child is node_ddd or child is node_ccc:
                continue

            assert not child.is_locked()

    def test_export_data(self):
        dico = self.tree.export_data()
        assert len(dico) == 5
        for key, (local, remote) in dico.items():
            assert key.endswith(remote[7:])
            assert key.endswith(local[6:])


class TestMergeMisc(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = AddedLocalFilesTask(container=None,
                                                target=("aaaa/bbb/ccc",),
                                                local_container=self.lc,
                                                create_mode=True)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_invalid_new_task(self):
        assert not self.tree._use_the_new_task(self.node, "new task")

    def test_invalid_task(self):
        self.node.waiting_task = "task"
        assert not self.tree._use_the_new_task(self.node, "new task")


class TestMergeFromLocalCreateTask(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = AddedLocalFilesTask(container=None,
                                                target=("aaaa/bbb/ccc",),
                                                local_container=self.lc,
                                                create_mode=True)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_delete_task_and_valid_remote_hash(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)

    def test_replace_with_a_local_delete_task_and_not_valid_remote_hash(self):
        self.node.set_hash(None, None)
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()


class TestMergeFromLocalUpdateTask(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = AddedLocalFilesTask(container=None,
                                                target=("aaaa/bbb/ccc",),
                                                local_container=self.lc,
                                                create_mode=False)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.current_task.create_mode
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.current_task.create_mode
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_delete_task_and_valid_remote_hash(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_delete_task_and_not_valid_remote_hash(self):
        self.node.set_hash(None, None)
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.current_task.create_mode
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.current_task.create_mode
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()


class TestMergeFromLocalRemoveTask(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = RemovedLocalFilesTask(container=None,
                                                  target=("aaaa/bbb/ccc",),
                                                  local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_delete_task(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()


class TestMergeFromRemoteAddTask(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = AddedRemoteFilesTask(container=None,
                                                 target=("aaaa/bbb/ccc",),
                                                 local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_delete_task(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task_and_valid_local_hash(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task_and_not_valid_local_hash(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        self.node.set_hash(None, "remote")
        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()


class TestMergeFromRemoteRemoveTask(object):

    def setup_method(self, method):
        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = RemovedRemoteFilesTask(container=None,
                                                   target=("aaaa/bbb/ccc",),
                                                   local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_local_delete_task(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert self.node.is_invalidate_local()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()


class TestMergeFromLocalMoveTaskOnSrc(object):

    def setup_method(self, method):
        global task_added

        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = MovedLocalFilesTask(container=None,
                                                target=("aaaa/bbb/ccc",
                                                        "aaaa/bbb/cccd"),
                                                local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

        del task_added[:]

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_delete_task(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_the_same_move(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)
        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd2"),
                                       local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.ft.cancel
        assert len(task_added) == 3

        targets = ["aaaa/bbb/ccc", "aaaa/bbb/cccd", "aaaa/bbb/cccd2"]
        for new_task, priority in task_added:
            assert priority
            assert isinstance(new_task, AddedLocalFilesTask)
            rel_path = new_task.target_list[0]
            assert rel_path in targets
            targets.remove(rel_path)

    def test_replace_with_a_move_as_src_task_with_dests_exist(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd2"),
                                       local_container=self.lc)

        node_cccd = self.tree.root.get_or_insert_node("aaaa/bbb/cccd")
        node_cccd.set_hash("local", "remote", False)
        node_cccd2 = self.tree.root.get_or_insert_node("aaaa/bbb/cccd2")
        node_cccd2.set_hash("local", "remote", False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.ft.cancel
        assert len(task_added) == 3
        assert node_cccd.is_invalidate_remote()
        assert node_cccd2.is_invalidate_remote()

        targets = ["aaaa/bbb/ccc", "aaaa/bbb/cccd", "aaaa/bbb/cccd2"]
        for new_task, priority in task_added:
            assert priority
            assert isinstance(new_task, AddedLocalFilesTask)
            rel_path = new_task.target_list[0]
            assert rel_path in targets
            targets.remove(rel_path)

    def test_replace_with_a_move_as_dst_task(self):
        global task_added

        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        old_dest = self.tree.root.get_or_insert_node(
            "aaaa/bbb/cccd",
            index_saver=self.fake_saver)
        old_dest.set_hash(None, "remote")

        assert self.tree._use_the_new_task(self.node, new_task)
        assert old_dest.is_invalidate_remote()
        assert len(task_added) == 1
        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, AddedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/cccd"


class TestMergeFromLocalMoveTaskOnDst(object):

    def setup_method(self, method):
        global task_added

        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = MovedLocalFilesTask(container=None,
                                                target=("aaaa/bbb/cccs",
                                                        "aaaa/bbb/ccc"),
                                                local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

        del task_added[:]

    def test_replace_with_a_local_create_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=True)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_update_task(self):
        new_task = AddedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",),
                                       local_container=self.lc,
                                       create_mode=False)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_local_delete_task(self):
        new_task = RemovedLocalFilesTask(container=None,
                                         target=("aaaa/bbb/ccc",),
                                         local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_local()
        assert not self.node.is_invalidate_remote()

    def test_replace_with_a_remote_add_task(self):
        new_task = AddedRemoteFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_remote_remove_task(self):
        new_task = RemovedRemoteFilesTask(container=None,
                                          target=("aaaa/bbb/ccc",),
                                          local_container=self.lc)

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_the_same_move(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)
        assert not self.tree._use_the_new_task(self.node, new_task)
        assert not self.node.is_invalidate_remote()
        assert not self.node.is_invalidate_local()

    def test_replace_with_a_move_as_src_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/ccc",
                                               "aaaa/bbb/cccd"),
                                       local_container=self.lc)

        node_cccs = self.tree.root.get_or_insert_node("aaaa/bbb/cccs")
        node_cccs.executing_task = self.current_task

        assert not self.tree._use_the_new_task(self.node, new_task)
        assert isinstance(self.node.waiting_task, RemovedLocalFilesTask)
        assert self.ft.cancel
        assert len(task_added) == 2

        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, RemovedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/ccc"

        new_task, priority = task_added[1]
        assert priority
        assert isinstance(new_task, MovedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/cccs"
        assert new_task.target_list[1] == "aaaa/bbb/cccd"

        assert node_cccs.executing_task is not None

    def test_replace_with_a_move_as_dst_task(self):
        new_task = MovedLocalFilesTask(container=None,
                                       target=("aaaa/bbb/cccs2",
                                               "aaaa/bbb/ccc"),
                                       local_container=self.lc)

        assert self.tree._use_the_new_task(self.node, new_task)
        assert len(task_added) == 1
        new_task, priority = task_added[0]
        assert priority
        assert isinstance(new_task, RemovedLocalFilesTask)
        assert new_task.target_list[0] == "aaaa/bbb/cccs"


class TestReplaceTask(object):

    def setup_method(self, method):
        global task_added

        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)
        self.lc = FakeLocalContainer()
        self.ft = FakeTask()

        self.current_task = AddedRemoteFilesTask(container=None,
                                                 target=("aaaa/bbb/ccc",),
                                                 local_container=self.lc)
        self.node.add_waiting_node(self)
        self.node.waiting_task = self.current_task
        self.node.waiting_task_callback = self.ft.callback
        self.node.set_hash("local", "remote")

        del task_added[:]

    def test_replace_task_with_create_task_and_cancel(self):
        self.tree._replace_task_with_create_task(self.node,
                                                 self.node.waiting_task,
                                                 True)
        assert self.ft.cancel
        assert isinstance(self.node.waiting_task, AddedLocalFilesTask)

    def test_replace_task_with_create_task_without_cancel(self):
        self.tree._replace_task_with_create_task(self.node,
                                                 self.node.waiting_task,
                                                 False)

        assert not self.ft.cancel
        assert isinstance(self.node.waiting_task, AddedLocalFilesTask)

    def test_replace_task_with_delete_task_and_cancel(self):
        self.tree._replace_task_with_delete_task(self.node,
                                                 self.node.waiting_task,
                                                 True)

        assert self.ft.cancel
        assert isinstance(self.node.waiting_task, RemovedLocalFilesTask)

    def test_replace_task_with_delete_task_without_cancel(self):
        self.tree._replace_task_with_delete_task(self.node,
                                                 self.node.waiting_task,
                                                 False)
        assert not self.ft.cancel
        assert isinstance(self.node.waiting_task, RemovedLocalFilesTask)


class TestAcquire(object):

    def setup_method(self, method):
        global task_added

        self.fake_saver = FakeIndexSaver()

        self.input_idx = {"aaaa/bbb/ccc": ["local_ccc", "remote_ccc"],
                          "aaaa/bbb/ddd": ["local_ddd", "remote_ddd"],
                          "aaaa/bbb/hhh": ["local_hhh", "remote_hhh"],
                          "fff/eee": ["local_eee", "remote_eee"],
                          "ggg": ["local_ggg", "remote_ggg"]}

        self.tree = IndexTree(self.fake_saver, self.input_idx)
        self.node = self.tree.root.get_or_insert_node("aaaa/bbb/ccc",
                                                      create=False)

        self.lc = FakeLocalContainer()
        self.task = AddedLocalFilesTask(container=None,
                                        target=("aaaa/bbb/ccc",),
                                        local_container=self.lc,
                                        create_mode=True)

        del task_added[:]

    def test_empty_aquire(self):
        p = self.tree.acquire((), "task")
        assert p.result() == {}
        for node in self.tree.root.traverse():
            assert not node.is_locked()

    def test_simple_aquire(self):
        self.tree.acquire(("aaaa/bbb/ccc",), "task")
        assert self.node.is_locked()
        assert self.tree.is_locked()

    def test_aquire_with_too_many_path(self):
        with pytest.raises(Exception):
            self.tree.acquire(("aaaa/bbb/ccc",
                               "aaaa/bbb/ccc1",
                               "aaaa/bbb/ccc2",
                               "aaaa/bbb/ccc3"), "task")

    def test_aquire_lock_already_acquired(self):
        self.node.lock(self.node, self.task)

        p = self.tree.acquire(("aaaa/bbb/ccc", ), self.task)
        r = p.result()
        assert isinstance(r, list)
        assert len(r) == 1

    def test_aquire_sync_task_on_parent(self):
        node_aaa = self.tree.root.get_or_insert_node("aaaa", create=False)
        node_aaa.waiting_task = "task"
        p = self.tree.acquire(("aaaa/bbb",), "task", prior_acquire=True)

        with pytest.raises(RedundantTaskInterruption):
            p.result()

    def test_acquire_a_task_already_waits_and_no_merge(self):
        self.node.waiting_task = self.task

        p = self.tree.acquire(
            ("aaaa/bbb/ccc",), self.task, prior_acquire=True)

        with pytest.raises(RedundantTaskInterruption):
            p.result()

    def test_acquire_a_task_already_waits_and_merge(self):
        task = RemovedRemoteFilesTask(container=None,
                                      target=("aaaa/bbb/ccc",),
                                      local_container=self.lc)
        task.prior = True

        fake_task = FakeTask()
        self.node.waiting_task = task
        self.node.waiting_task_callback = fake_task.callback
        self.tree.acquire(("aaaa/bbb/ccc",), self.task, prior_acquire=True)

        assert fake_task.cancel
        assert self.node.waiting_task is self.task

    def test_acquire_nodes_is_locked_but_no_waiting_task(self):
        node_ccc = self.tree.root.get_or_insert_node("aaaa/bbb/ccc")
        owner = FakeDirectoryNode()
        node_ccc.lock(owner)
        p = self.tree.acquire(("aaaa/bbb/ccc",), self.task)
        node_ccc.unlock(owner)
        node_ccc.trigger_waiting_task()
        assert isinstance(p.result(), list)

    def test_acquire_a_parent_is_locked(self):
        node_aaa = self.tree.root.get_or_insert_node("aaaa", create=False)
        node_aaa.lock()
        p = self.tree.acquire(("aaaa/1234",), self.task)
        node_aaa.unlock()

        node_aaa.trigger_waiting_nodes()
        assert isinstance(p.result(), list)

    def test_acquire_a_child_is_locked(self):
        node_ccc = self.tree.root.get_or_insert_node("aaaa/bbb/ccc")
        node_ccc.lock()
        p = self.tree.acquire((".",), "task")
        node_ccc.unlock()
        node_ccc.trigger_waiting_nodes()
        assert isinstance(p.result(), list)
