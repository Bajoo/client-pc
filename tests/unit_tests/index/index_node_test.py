#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.index.index_node import AbstractNode
from bajoo.index.index_node import DirectoryNode
from bajoo.index.index_node import FileNode
from bajoo.index.index_node import split_path

from .fake_index_saver import FakeIndexSaver
from .fake_task import FakeTask
from .fake_directory_node import FakeDirectoryNode


class TestSplitPath(object):

    def test_none_path(self):
        assert split_path(None) == ()

    def test_empty_path1(self):
        assert split_path("") == ()

    def test_empty_path2(self):
        assert split_path(".") == ()

    def test_empty_path3(self):
        assert split_path("/") == ()

    def test_simple_path1(self):
        assert split_path("path_part") == ("path_part",)

    def test_simple_path2(self):
        assert split_path("./path_part") == ("path_part",)

    def test_simple_path3(self):
        assert split_path("/path_part") == ("path_part",)

    def test_complex_path1(self):
        assert split_path("path_part1/path_part2/path_part3") == ("path_part1",
                                                                  "path_part2",
                                                                  "path_part3")

    def test_complex_path2(self):
        assert split_path(
            "./path_part1/path_part2/path_part3") == ("path_part1",
                                                      "path_part2",
                                                      "path_part3",)

    def test_complex_path3(self):
        assert split_path(
            "/path_part1/path_part2/path_part3") == ("path_part1",
                                                     "path_part2",
                                                     "path_part3",)


class FakeNodeForAbstractTest(object):

    def __init__(self):
        self.increase_prior_for = None
        self.remove_node = None
        self.cancel = None
        self.release_aquired_lock = None

    def set_prior(self, node):
        self.increase_prior_for = node

    def remove_waiting_node(self, node):
        self.remove_node = node

    def callback(self, cancel=False, release_aquired_lock=True):
        self.cancel = cancel
        self.release_aquired_lock = release_aquired_lock


class TestGet_or_insert_node(object):

    def test_getinsert_empty_path_and_exist(self):
        node = DirectoryNode("", None)
        assert node.get_or_insert_node("") is node

    def test_getinsert_single_path_and_exist(self):
        node = DirectoryNode("single", None)
        sub_node = node.get_or_insert_node("single")
        assert sub_node is not node
        assert "single" in node.children
        assert isinstance(node.children["single"], FileNode)

    def test_getinsert_single_path_and_not_exist_and_only_directory(self):
        node = DirectoryNode("", None)
        sub_node = node.get_or_insert_node("single", only_directory=True)
        assert sub_node is not node
        assert "single" in node.children
        assert isinstance(node.children["single"], DirectoryNode)

    def test_getinsert_long_path_and_exist(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2
        node3 = DirectoryNode("part2", node2)
        node2.children["part2"] = node3
        node4 = DirectoryNode("part3", node3)
        node3.children["part3"] = node4

        sub_node = node1.get_or_insert_node("part1/part2/part3/")
        assert sub_node is node4

    def test_getinsert_long_path_and_last_leaf_not_exist(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2
        node3 = DirectoryNode("part2", node2)
        node2.children["part2"] = node3

        sub_node = node1.get_or_insert_node("part1/part2/part3/")
        assert sub_node is not None
        assert isinstance(sub_node, FileNode)
        assert sub_node.parent is node3
        assert "part3" in node3.children
        assert node3.children["part3"] is sub_node

    def test_getinsert_long_path_and_last_leaf_not_exist_and_no_create(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2
        node3 = DirectoryNode("part2", node2)
        node2.children["part2"] = node3

        sub_node = node1.get_or_insert_node(
            "part1/part2/part3/", create=False)
        assert sub_node is None
        assert "part3" not in node3.children

    def test_getinsert_long_path_and_last_leaf_not_exist_only_directory(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2
        node3 = DirectoryNode("part2", node2)
        node2.children["part2"] = node3

        sub_node = node1.get_or_insert_node(
            "part1/part2/part3/", only_directory=True)
        assert sub_node is not None
        assert isinstance(sub_node, DirectoryNode)
        assert sub_node.parent is node3
        assert "part3" in node3.children
        assert node3.children["part3"] is sub_node

    def test_getinsert_last_two_part_do_not_exist(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2

        sub_node = node1.get_or_insert_node("part1/part2/part3/")
        assert sub_node is not None
        assert isinstance(sub_node, FileNode)
        sub_node_parent = sub_node.parent
        assert sub_node_parent is not None
        assert sub_node_parent.parent is node2
        assert "part2" in node2.children
        assert node2.children["part2"] is sub_node_parent

    def test_getinsert_last_two_part_not_exist_no_create(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2

        sub_node = node1.get_or_insert_node(
            "part1/part2/part3/", create=False)
        assert sub_node is None
        assert len(node2.children) == 0

    def test_getinsert_last_two_parts_not_exist_only_directory(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("part1", node1)
        node1.children["part1"] = node2

        sub_node = node1.get_or_insert_node(
            "part1/part2/part3/", only_directory=True)
        assert sub_node is not None
        assert isinstance(sub_node, DirectoryNode)
        sub_node_parent = sub_node.parent
        assert sub_node_parent is not None
        assert sub_node_parent.parent is node2
        assert "part2" in node2.children
        assert node2.children["part2"] is sub_node_parent


class FullAbstractNode(AbstractNode):
    def remove_child(self, node=None):
        pass

    def add_waiting_node(self, node=None):
        pass

    def remove_waiting_node(self, node=None):
        pass

    def trigger_waiting_nodes(self):
        pass

    def set_prior(self, node=None):
        pass

    def traverse_only_directory_node(self):
        pass

    def traverse_only_file_node(self):
        pass


class TestAbstractNode(object):

    def test_init(self):
        node = FullAbstractNode("path_part", "parent")
        assert node.parent == "parent"
        assert node.lock_owner is None
        assert node.executing_task is None
        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is None
        assert node.path_part == "path_part"

    def test_get_complete_path1(self):
        node1 = FullAbstractNode("", None)
        node2 = FullAbstractNode("path_part2", node1)
        node3 = FullAbstractNode("path_part3", node2)

        result = "path_part2/path_part3"
        assert node3.get_complete_path() == result

    def test_get_complete_path2(self):
        node1 = FullAbstractNode("", None)
        node2 = FullAbstractNode("path_part", node1)

        assert node2.get_complete_path() == "path_part"

    def test_get_complete_path3(self):
        node = FullAbstractNode("", None)

        assert node.get_complete_path() == "."

    def test_str(self):
        node1 = FullAbstractNode("", None)
        node2 = FullAbstractNode("path_part2", node1)
        node3 = FullAbstractNode("path_part3", node2)

        assert node3.get_complete_path() == str(node3)

    def test_repr(self):
        node1 = FullAbstractNode("", None)
        node2 = FullAbstractNode("path_part2", node1)
        node3 = FullAbstractNode("path_part3", node2)

        assert node3.get_complete_path() == repr(node3)

    def test_is_removable_no_parent(self):
        node = FullAbstractNode("path_part", None)
        assert not node.is_removable()

    def test_is_removable_locked(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock()
        assert not node.is_removable()

    def test_is_removable_waiting_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.waiting_task = "waiting"
        assert not node.is_removable()

    def test_is_removable_success(self):
        node = FullAbstractNode("path_part", "parent_node")
        assert node.is_removable()

    def test_lock_no_owner_no_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock()
        assert node.is_lock_owner()
        assert node.executing_task is None

    def test_lock_owner_no_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock("owner")
        assert not node.is_lock_owner()
        assert node.lock_owner == "owner"
        assert node.executing_task is None

    def test_lock_no_owner_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock(executing_task="task")
        assert node.is_lock_owner()
        assert node.executing_task == "task"

    def test_lock_owner_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock("owner", "task")
        assert not node.is_lock_owner()
        assert node.lock_owner == "owner"
        assert node.executing_task is None

    def test_lock_self_owner_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock(node, "task")
        assert node.is_lock_owner()
        assert node.executing_task == "task"

    def test_unlock_not_locked(self):
        node = FullAbstractNode("path_part", "parent_node")
        assert not node.is_lock_owner()
        assert node.lock_owner is None
        assert node.executing_task is None
        node.unlock()
        assert not node.is_lock_owner()
        assert node.lock_owner is None
        assert node.executing_task is None

    def test_unlock_locked_but_not_owner(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock("owner", "task")
        assert not node.is_lock_owner()
        assert node.lock_owner == "owner"
        assert node.executing_task is None
        node.unlock()
        assert not node.is_lock_owner()
        assert node.lock_owner == "owner"
        assert node.executing_task is None

    def test_unlock_locked_but_and_owner(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock(node, "task")
        assert node.is_lock_owner()
        assert node.executing_task is "task"
        node.unlock()
        assert not node.is_lock_owner()
        assert node.lock_owner is None
        assert node.executing_task is None

    def test_trigger_no_waiting_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.trigger_waiting_task()

    def test_trigger_waiting_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        fake_node = FakeNodeForAbstractTest()

        node.waiting_task_callback = fake_node.callback
        node.waiting_task = "task"
        node.waiting_for_node = fake_node

        node.trigger_waiting_task()

        assert node.waiting_task_callback is None
        assert node.waiting_task is None
        assert node.waiting_for_node is None
        assert not fake_node.cancel
        assert fake_node.release_aquired_lock

    def test_is_locked_but_not_locked(self):
        node = FullAbstractNode("path_part", "parent_node")
        assert not node.is_locked()

    def test_is_locked_and_locked(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock()
        assert node.is_locked()

    def test_is_locked_and_unlocked_after_a_lock(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.lock()
        node.unlock()
        assert not node.is_locked()

    def test_empty_test_add_waiting_node(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.add_waiting_node(node)

    def test_empty_test_remove_waiting_node(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.remove_waiting_node()

    def test_set_prior_no_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        assert node.waiting_for_node is None
        node.set_prior()

    def test_cancel_task_no_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        fake_node = FakeNodeForAbstractTest()
        node.waiting_for_node = fake_node
        node.cancel_waiting_task()
        assert fake_node.remove_node is None

    def test_cancel_task_with_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        fake_node = FakeNodeForAbstractTest()
        node.waiting_task = "task"
        node.waiting_for_node = fake_node
        node.waiting_task_callback = fake_node.callback

        node.cancel_waiting_task()
        assert fake_node.remove_node is node
        assert fake_node.cancel
        assert fake_node.release_aquired_lock

        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is None

    def test_cancel_task_with_task_and_no_remove_from_waiting_list(self):
        node = FullAbstractNode("path_part", "parent_node")
        fake_node = FakeNodeForAbstractTest()
        node.waiting_task = "task"
        node.waiting_for_node = fake_node
        node.waiting_task_callback = fake_node.callback

        node.cancel_waiting_task(remove_from_waiting_list=False)
        assert fake_node.remove_node is None
        assert fake_node.cancel
        assert fake_node.release_aquired_lock

        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is fake_node

    def test_cancel_task_with_task_and_release_acquired_lock_disabled(self):
        node = FullAbstractNode("path_part", "parent_node")
        fake_node = FakeNodeForAbstractTest()
        node.waiting_task = "task"
        node.waiting_for_node = fake_node
        node.waiting_task_callback = fake_node.callback

        node.cancel_waiting_task(release_aquired_lock=False)
        assert fake_node.remove_node is node
        assert fake_node.cancel
        assert not fake_node.release_aquired_lock

        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is None

    def test_empty_test_remove_child(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.remove_child(node)

    def test_set_waiting_task(self):
        node = FullAbstractNode("path_part", "parent_node")
        node.set_waiting_task("task", "callback")
        assert node.waiting_task == "task"
        assert node.waiting_task_callback == "callback"

    def test_traverse_node_included(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        result = list(node.traverse())

        assert len(result) == 1
        assert node in result

    def test_traverse_node_excluded(self):
        node = FileNode("part", "saver", "parent", "rel_path")

        result = list(node.traverse(collect=lambda x: False))
        assert len(result) == 0


class TestDirectoryNode(object):

    def test_init(self):
        node = DirectoryNode("path_part")
        assert isinstance(node.children, dict)
        assert len(node.children) == 0
        assert isinstance(node.waiting_nodes, list)
        assert len(node.waiting_nodes) == 0
        assert node.locked_children == 0

    def test_is_removable(self):
        node = DirectoryNode("path_part", "parent")
        assert node.is_removable()

    def test_is_removable_with_waiting_node(self):
        node = DirectoryNode("path_part", "parent")
        node.children["child"] = "child"
        assert not node.is_removable()

    def test_is_removable_with_children(self):
        node = DirectoryNode("path_part", "parent")
        node.waiting_nodes.append("waiting_node")
        assert not node.is_removable()

    def test_unlock_not_locked(self):
        node = DirectoryNode("path_part", "parent")
        child = FakeDirectoryNode()
        node.children["child"] = child
        node.unlock()
        assert child.unlocker is None

    def test_unlock_locked_by_another_node(self):
        node = DirectoryNode("path_part", "parent")
        child = FakeDirectoryNode()
        node.children["child"] = child
        node.lock("lock_owner")
        node.unlock()
        assert child.unlocker is None

    def test_unlock_locked_by_itself(self):
        node = DirectoryNode("path_part", "parent")
        child = FakeDirectoryNode()
        node.children["child"] = child
        node.lock()
        node.unlock()
        assert child.unlocker is node

    def test_has_children_unlocked_no_children(self):
        node = DirectoryNode("path_part", "parent")
        assert not node.has_children_unlocked()

    def test_has_children_unlocked_with_children(self):
        node = DirectoryNode("path_part", "parent")
        node.children["child"] = "child"
        assert node.has_children_unlocked()

    def test_increment_children_locked_count_with_no_child(self):
        node = DirectoryNode("path_part", "parent")
        assert not node.has_children_unlocked()
        node.increment_children_locked_count()
        assert not node.has_children_unlocked()

    def test_increment_children_locked_count_with_unlocked_child(self):
        node = DirectoryNode("path_part", "parent")
        node.children["child"] = "child"
        assert node.has_children_unlocked()
        node.increment_children_locked_count()
        assert not node.has_children_unlocked()

    def test_trigger_with_no_waiting_nodes(self):
        node = DirectoryNode("path_part", "parent")
        node.trigger_waiting_task()

    def test_trigger_with_itself_waiting(self):
        node = DirectoryNode("path_part", "parent")
        node.waiting_nodes.append(node)
        fake_node = FakeNodeForAbstractTest()
        node.waiting_task = "task"
        node.waiting_for_node = self
        node.waiting_task_callback = fake_node.callback
        node.trigger_waiting_task()

        assert node.waiting_task_callback is None
        assert node.waiting_task is None
        assert node.waiting_for_node is None
        assert not fake_node.cancel
        assert fake_node.release_aquired_lock

    def test_trigger_with_other_node_waiting(self):
        node = DirectoryNode("path_part", "parent")
        fake_node = FakeDirectoryNode()
        node.waiting_nodes.append(fake_node)
        node.trigger_waiting_nodes()
        assert fake_node.triggered

    def test_add_waiting_node_to_this_node_not_prior(self):
        node = DirectoryNode("path_part", None)
        node.lock()

        node2 = DirectoryNode("path_part2", node)
        node.add_waiting_node(node2)

        assert node2 in node.waiting_nodes

        node3 = DirectoryNode("path_part3", node)
        node.add_waiting_node(node3, prior_node=False)

        assert node3 in node.waiting_nodes
        assert node3 is node.waiting_nodes[-1]

    def test_add_waiting_node_to_this_node_prior(self):
        node = DirectoryNode("path_part", None)
        node.lock()

        node2 = DirectoryNode("path_part2", node)
        node.add_waiting_node(node2)

        assert node2 in node.waiting_nodes

        node4 = DirectoryNode("path_part4", node)
        node.add_waiting_node(node4, prior_node=True)

        assert node4 in node.waiting_nodes
        assert node4 is node.waiting_nodes[0]

    def test_add_waiting_node_to_another_node_not_prior(self):
        node = DirectoryNode("path_part", None)
        fake_node = FakeDirectoryNode()
        node.lock(fake_node)

        node2 = DirectoryNode("path_part2", node)
        node.add_waiting_node(node2)

        assert (node2, False,) in fake_node.waiting_nodes

        node3 = DirectoryNode("path_part3", node)
        node.add_waiting_node(node3, prior_node=False)

        assert (node3, False,) in fake_node.waiting_nodes
        assert (node3, False,) == fake_node.waiting_nodes[-1]

    def test_add_waiting_node_to_another_node_prior(self):
        node = DirectoryNode("path_part", None)
        fake_node = FakeDirectoryNode()
        node.lock(fake_node)

        node2 = DirectoryNode("path_part2", node)
        node.add_waiting_node(node2)

        assert (node2, False,) in fake_node.waiting_nodes

        node3 = DirectoryNode("path_part3", node)
        node.add_waiting_node(node3, prior_node=True)

        assert (node3, True,) in fake_node.waiting_nodes
        assert (node3, True,) == fake_node.waiting_nodes[-1]

    def test_remove_waiting_node_no_waiting(self):
        node = DirectoryNode("path_part", None)
        node.remove_waiting_node()

    def test_remove_waiting_node_waiting_on_itself(self):
        node = DirectoryNode("path_part", None)
        node.lock()
        node.add_waiting_node(node)
        assert node in node.waiting_nodes
        assert node is node.waiting_for_node
        node.remove_waiting_node()
        assert node not in node.waiting_nodes
        assert node.waiting_for_node is None

    def test_remove_waiting_node_waiting_on_another_node(self):
        node1 = DirectoryNode("path_part1", None)
        node2 = DirectoryNode("path_part2", node1)
        node2.lock(node1)
        node2.add_waiting_node(node2)
        assert node2 in node1.waiting_nodes
        assert node1 is node2.waiting_for_node
        node2.remove_waiting_node()
        assert node2 not in node1.waiting_nodes
        assert node2.waiting_for_node is None

    def test_set_prior_no_waiting(self):
        node = DirectoryNode("path_part", None)
        node.set_prior()

    def test_set_prior_waiting_on_itself(self):
        node = DirectoryNode("path_part", None)
        node.lock()
        node.waiting_nodes.append("another task")
        node.add_waiting_node(node)
        assert node in node.waiting_nodes
        assert node is node.waiting_nodes[1]
        assert node is node.waiting_for_node
        node.set_prior()
        assert node in node.waiting_nodes
        assert node is node.waiting_nodes[0]
        assert node is node.waiting_for_node

    def test_set_prior_waiting_on_another_node(self):
        node1 = DirectoryNode("path_part1", None)
        node2 = DirectoryNode("path_part2", node1)
        node2.lock(node1)
        node1.waiting_nodes.append("another task")
        node2.add_waiting_node(node2)
        assert node2 in node1.waiting_nodes
        assert node2 is node1.waiting_nodes[1]
        assert node1 is node2.waiting_for_node
        node2.set_prior()
        assert node2 in node1.waiting_nodes
        assert node2 is node1.waiting_nodes[0]
        assert node1 is node2.waiting_for_node

    def test_traverse_empty_tree(self):
        node = DirectoryNode("", None)
        node_list = list(node.traverse())
        assert len(node_list) == 1
        assert node in node_list

    def test_traverse_do_not_explore_self(self):
        node = DirectoryNode("", None)
        node_list = list(node.traverse(explore=lambda x: False))
        assert len(node_list) == 0

    def test_traverse_only_dir_tree(self):
        node1 = DirectoryNode("", None)
        node2 = node1.get_or_insert_node("part1/part2/part3")
        node5 = node1.get_or_insert_node("part1/part6/part7")
        node6 = node1.get_or_insert_node("part8/part9")
        node8 = node1.get_or_insert_node("part11", only_directory=True)

        def collect(node):
            return isinstance(node, DirectoryNode)

        node_list = list(node1.traverse(collect=collect))
        assert len(node_list) == 6
        assert node1 in node_list
        assert node2.parent in node_list
        assert node2.parent.parent in node_list
        assert node5.parent in node_list
        assert node6.parent in node_list
        assert node8 in node_list

    def test_traverse_various_node_tree(self):
        node1 = DirectoryNode("", None)
        node2 = node1.get_or_insert_node("part1/part2/part3")
        node3 = node1.get_or_insert_node("part1/part2/part4")
        node4 = node1.get_or_insert_node("part1/part2/part5")
        node5 = node1.get_or_insert_node("part1/part6/part7")
        node6 = node1.get_or_insert_node("part8/part9")
        node7 = node1.get_or_insert_node("part10")

        def collect(node):
            return isinstance(node, FileNode)

        node_list = list(node1.traverse(collect=collect))
        assert len(node_list) == 6
        assert node2 in node_list
        assert node3 in node_list
        assert node4 in node_list
        assert node5 in node_list
        assert node6 in node_list
        assert node7 in node_list

    def test_self_remove_if_possible(self):
        node1 = DirectoryNode("", None)
        node2 = DirectoryNode("path_part2", node1)
        node1.children[node2.path_part] = node2
        node3 = DirectoryNode("path_part3", node2)
        node2.children[node3.path_part] = node3

        node3.self_remove_if_possible()
        assert len(node1.children) == 0


class TestFileNode(object):

    def test_init(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        assert node is not None
        assert node.local_md5 is None
        assert node.remote_md5 is None
        assert node.waiting_sync_node is None
        assert not node.self_waiting
        assert not node.do_invalidate_local
        assert node.index_saver == "saver"

    def test_set_hash(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        assert fake_saver.triggered == 0
        assert node.local_md5 is None
        assert node.remote_md5 is None

        node.set_hash("local", "remote")

        assert fake_saver.triggered == 1
        assert node.local_md5 == "local"
        assert node.remote_md5 == "remote"

    def test_is_removable1(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        assert node.is_removable()

    def test_is_removable2(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")
        assert not node.is_removable()

    def test_is_removable3(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.self_waiting = True
        assert not node.is_removable()

    def test_is_removable4(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.waiting_sync_node = 42
        assert not node.is_removable()

    def test_trigger_nothing_to_trigger(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.trigger_waiting_nodes()

    def test_trigger_self_to_trigger(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.self_waiting = True
        fake_task = FakeTask()
        node.waiting_task = fake_task
        node.waiting_task_callback = fake_task.callback
        node.waiting_for_node = self
        node.trigger_waiting_nodes()

        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is None
        assert not node.self_waiting
        assert fake_task.callback_called

    def test_trigger_sync_to_trigger(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.self_waiting = True
        node.waiting_sync_node = FakeDirectoryNode()
        fake_task = FakeTask()
        node.waiting_task = fake_task
        node.waiting_task_callback = fake_task.callback
        node.waiting_for_node = self

        node.trigger_waiting_nodes()

        assert node.waiting_sync_node is not None
        assert not node.waiting_sync_node.triggered
        assert node.waiting_task is None
        assert node.waiting_task_callback is None
        assert node.waiting_for_node is None
        assert not node.self_waiting
        assert fake_task.callback_called

    def test_trigger_self_and_sync_to_trigger(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.self_waiting = False
        fake_node = FakeDirectoryNode()
        node.waiting_sync_node = fake_node

        node.trigger_waiting_nodes()

        assert node.waiting_sync_node is None
        assert fake_node.triggered

    def test_add_waiting_node_self_nothing_wait(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.add_waiting_node(node)
        assert node.self_waiting
        assert node.waiting_for_node is node

    def test_add_waiting_node_self_sync_wait(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.waiting_sync_node = fake_dir_node

        node.add_waiting_node(node)

        assert len(fake_dir_node.waiting_nodes) == 1
        assert fake_dir_node.waiting_nodes[0] == (node, False)
        assert node.waiting_for_node is None

    def test_add_waiting_node_self_sync_wait_and_prior(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.waiting_sync_node = fake_dir_node

        node.add_waiting_node(node, prior_node=True)

        assert len(fake_dir_node.waiting_nodes) == 0
        assert node.self_waiting
        assert node.waiting_for_node is node

    def test_add_waiting_node_sync_nothing_wait(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.add_waiting_node(fake_dir_node)

        assert node.waiting_sync_node is fake_dir_node
        assert fake_dir_node.waiting_for_node is node

    def test_add_waiting_node_sync_self_wait(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.add_waiting_node(node)
        fake_dir_node = FakeDirectoryNode()
        node.add_waiting_node(fake_dir_node)

        assert node.self_waiting
        assert node.waiting_sync_node is fake_dir_node
        assert fake_dir_node.waiting_for_node is node

    def test_add_waiting_node_sync_self_wait_and_prior(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.add_waiting_node(node)
        fake_dir_node = FakeDirectoryNode()
        node.add_waiting_node(fake_dir_node, prior_node=True)

        assert not node.self_waiting
        assert node.waiting_sync_node is fake_dir_node
        assert fake_dir_node.waiting_for_node is node
        assert len(fake_dir_node.waiting_nodes) == 1
        assert fake_dir_node.waiting_nodes[0] == (node, False)

    def test_remove_waiting_node_no_waiting(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.remove_waiting_node()
        node.remove_waiting_node(42)

        assert node.waiting_sync_node is None
        assert not node.self_waiting
        assert node.waiting_for_node is None

    def test_remove_waiting_node_self_waiting(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.add_waiting_node(node)
        node.remove_waiting_node(node)

        assert node.waiting_sync_node is None
        assert not node.self_waiting
        assert node.waiting_for_node is None

    def test_remove_waiting_node_sync_waiting(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.add_waiting_node(fake_dir_node)
        node.remove_waiting_node(fake_dir_node)

        assert node.waiting_sync_node is None
        assert not node.self_waiting
        assert fake_dir_node.waiting_for_node is None

    def test_remove_waiting_node_node_waits_for_a_sync(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.waiting_for_node = fake_dir_node
        node.remove_waiting_node(42)

        assert len(fake_dir_node.removed_nodes) == 1
        assert 42 in fake_dir_node.removed_nodes

    def test_set_prior_no_waiting(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        node.set_prior()

    def test_set_prior_waiting_to_another_node(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()
        node.waiting_for_node = fake_dir_node
        node.set_prior()

        assert len(fake_dir_node.prior_nodes) == 1
        assert node in fake_dir_node.prior_nodes

    def test_set_prior_self_waiting(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()

        node.add_waiting_node(fake_dir_node, prior_node=True)
        node.add_waiting_node(node)

        node.set_prior()

        assert len(fake_dir_node.waiting_nodes) == 1
        assert fake_dir_node.waiting_nodes[0] == (node, False)

        assert len(fake_dir_node.removed_nodes) == 1
        assert node in fake_dir_node.removed_nodes

        assert node.self_waiting
        assert node.waiting_sync_node is fake_dir_node

    def test_set_prior_on_sync_sync_waiting_first(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()

        node.add_waiting_node(fake_dir_node)
        node.add_waiting_node(node, prior_node=True)

        node.set_prior(fake_dir_node)

        assert len(fake_dir_node.waiting_nodes) == 1
        assert fake_dir_node.waiting_nodes[0] == (node, False)
        assert len(fake_dir_node.removed_nodes) == 1
        assert node in fake_dir_node.removed_nodes

        assert not node.self_waiting
        assert node.waiting_sync_node is fake_dir_node

    def test_set_prior_on_sync_sync_prior(self):
        node = FileNode("part", "saver", "parent", "rel_path")
        fake_dir_node = FakeDirectoryNode()

        node.add_waiting_node(node)
        node.add_waiting_node(fake_dir_node, prior_node=True)

        node.set_prior(fake_dir_node)

        assert len(fake_dir_node.waiting_nodes) == 1
        assert fake_dir_node.waiting_nodes[0] == (node, False)
        assert len(fake_dir_node.removed_nodes) == 0

        assert not node.self_waiting
        assert node.waiting_sync_node is fake_dir_node

    def test_unlock_not_locked(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")
        node.unlock()

        assert node.lock_owner is None
        assert node.local_md5 == "local"

    def test_unlock_locked_by_anoter_node(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.lock("owner")
        node.unlock()

        assert node.lock_owner == "owner"
        assert node.local_md5 == "local"

    def test_unlock_locked_by_self_node(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.lock()
        node.unlock()

        assert node.lock_owner is None
        assert node.local_md5 == "local"

    def test_invalidate_local_locked_node(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.lock()
        node.invalidate_local()
        assert node.is_invalidate_local()
        assert not node.is_invalidate_remote()
        node.unlock()

        assert node.lock_owner is None
        assert node.local_md5 is None
        assert node.remote_md5 == "remote"
        assert not node.do_invalidate_local
        assert node.is_invalidate_local()
        assert not node.is_invalidate_remote()

    def test_invalidate_remote_locked_node(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.lock()
        node.invalidate_remote()
        assert not node.is_invalidate_local()
        assert node.is_invalidate_remote()
        node.unlock()

        assert node.lock_owner is None
        assert node.local_md5 is "local"
        assert node.remote_md5 is None
        assert not node.do_invalidate_local
        assert not node.is_invalidate_local()
        assert node.is_invalidate_remote()

    def test_invalidate_local_not_locked(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.invalidate_local()
        assert node.local_md5 is None
        assert not node.do_invalidate_local
        assert node.is_invalidate_local()
        assert not node.is_invalidate_remote()

    def test_invalidate_remote_not_locked(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        node.set_hash("local", "remote")

        node.invalidate_remote()
        assert node.remote_md5 is None
        assert not node.do_invalidate_remote
        assert not node.is_invalidate_local()
        assert node.is_invalidate_remote()

    def test_invalidate_at_create(self):
        fake_saver = FakeIndexSaver()
        node = FileNode("part", fake_saver, "parent", "rel_path")
        assert node.is_invalidate_local()
        assert node.is_invalidate_remote()


class TestCollect(object):

    def test_traverse_only_directory_node(self):
        node1 = DirectoryNode("", None)
        node2 = node1.get_or_insert_node("part1/part2/part3")
        node5 = node1.get_or_insert_node("part1/part6/part7")
        node6 = node1.get_or_insert_node("part8/part9")

        node_list = list(node1.traverse_only_directory_node())

        assert len(node_list) == 5
        assert node1 in node_list
        assert node2.parent in node_list
        assert node2.parent.parent in node_list
        assert node5.parent in node_list
        assert node6.parent in node_list

    def test_traverse_only_file_node(self):
        node1 = DirectoryNode("", None)
        node2 = node1.get_or_insert_node("part1/part2/part3")
        node3 = node1.get_or_insert_node("part1/part2/part4")
        node4 = node1.get_or_insert_node("part1/part2/part5")
        node5 = node1.get_or_insert_node("part1/part6/part7")
        node6 = node1.get_or_insert_node("part8/part9")
        node7 = node1.get_or_insert_node("part10")

        node_list = list(node1.traverse_only_file_node())

        assert len(node_list) == 6
        for node in (node2, node3, node4, node5, node6, node7):
            assert node in node_list
