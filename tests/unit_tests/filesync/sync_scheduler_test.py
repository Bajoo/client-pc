# -*- coding: utf-8 -*-

from bajoo.filesync.sync_scheduler import SyncScheduler
from bajoo.index import IndexTree


class FakeNode(object):
    @classmethod
    def make_list(cls, nb):
        return list(cls() for _i in range(nb))


class FakeTree(object):
    def __init__(self, nodes):
        self.nodes = nodes[:]

    def browse_all_non_sync_nodes(self):
        try:
            yield self.nodes.pop(0)
        except IndexError:
            return


class TestSyncScheduler(object):

    def test_get_node_without_tree(self):
        scheduler = SyncScheduler()
        assert scheduler.get_node() == (None, None)

    def test_add_node_and_get_node(self):
        scheduler = SyncScheduler()
        nodes = FakeNode.make_list(3)
        scheduler.add_index_tree(FakeTree(nodes))

        list_nodes = []
        index_tree, node = scheduler.get_node()
        while node is not None:
            list_nodes.append(node)
            index_tree, node = scheduler.get_node()
        assert list_nodes == nodes

    def test_remove_index_tree_not_in_scheduler(self):
        fake_tree = object()
        scheduler = SyncScheduler()
        scheduler.remove_index_tree(fake_tree)

    def test_get_node_from_two_trees(self):
        scheduler = SyncScheduler()
        scheduler.add_index_tree(FakeTree(FakeNode.make_list(3)))
        scheduler.add_index_tree(FakeTree(FakeNode.make_list(4)))

        nb_nodes = 0
        while scheduler.get_node() != (None, None):
            nb_nodes += 1
        assert nb_nodes is 7

    def test_get_node_then_remove_index_tree(self):
        fake_tree = FakeTree(FakeNode.make_list(5))
        scheduler = SyncScheduler()
        scheduler.add_index_tree(fake_tree)

        assert scheduler.get_node()[1]
        assert scheduler.get_node()[1]
        scheduler.remove_index_tree(fake_tree)
        assert scheduler.get_node() == (None, None)

    def test_get_node_must_avoid_bloqued_trees(self):
        # first tree is blocked; only the second will be used.
        scheduler = SyncScheduler()
        scheduler.add_index_tree(FakeTree([IndexTree.WAIT_FOR_TASK]))
        scheduler.add_index_tree(FakeTree(FakeNode.make_list(3)))
        for i in range(3):
            index_tree, node = scheduler.get_node()
            assert isinstance(node, FakeNode)
            assert isinstance(index_tree, FakeTree)

        # second tree is blocked; only the first will be used.
        scheduler = SyncScheduler()
        scheduler.add_index_tree(FakeTree(FakeNode.make_list(3)))
        scheduler.add_index_tree(FakeTree([IndexTree.WAIT_FOR_TASK]))
        for i in range(3):
            index_tree, node = scheduler.get_node()
            assert isinstance(node, FakeNode)
            assert isinstance(index_tree, FakeTree)

    def test_get_node_return_none_when_all_trees_are_blocked(self):
        scheduler = SyncScheduler()
        scheduler.add_index_tree(FakeTree([FakeNode(),
                                           IndexTree.WAIT_FOR_TASK]))
        scheduler.add_index_tree(FakeTree([FakeNode(),
                                           IndexTree.WAIT_FOR_TASK]))

        assert isinstance(scheduler.get_node()[1], FakeNode)
        assert isinstance(scheduler.get_node()[1], FakeNode)
        assert scheduler.get_node() == (None, None)
