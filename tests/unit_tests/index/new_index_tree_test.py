# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from bajoo.index.base_node import BaseNode
from bajoo.index.new_index_tree import IndexTree


class MyNode(BaseNode):
    pass


def _make_tree(node_def, default_sync=False):
    """Quick helper to generate a BaseNode hierarchy.

    Args:
        Tuple[str, List[Tuple], bool]: node definition, of the form:
            ('node name', [children definitions], sync). Both part 2 and 3
            of the tuple are optional.
        default_sync (bool, optional): default value to set the 'sync' flag
    Returns:
        BaseNode: node built from the definition.
    """
    name = node_def[0]
    children = node_def[1] if len(node_def) > 1 else []
    sync_flag = node_def[2] if len(node_def) > 2 else default_sync
    node = BaseNode(name)
    node.sync = sync_flag
    for child_def in children:
        node.add_child(_make_tree(child_def, default_sync))
    return node


class TestBrowseIndexTree(object):
    """Test of the IndexTree.browse_all_non_sync_nodes() method."""

    def test_browse_empty_tree_will_return_empty_generator(self):
        tree = IndexTree()
        gen = tree.browse_all_non_sync_nodes()
        assert list(gen) == []

    def test_browse_clean_tree_returns_empty_generator(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [
            ('A', [('1',), ('2',)]),
            ('B', [('1',), ('2',)]),
        ]), default_sync=True)

        gen = tree.browse_all_non_sync_nodes()
        assert list(gen) == []

    def test_browse_dirty_tree_returns_only_non_sync_nodes(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [
            ('A', [('A1', [], False), ('A2',)]),
            ('B', [('B1',), ('B2', [], False)], False),
            ('C', [('C1', [], False), ('C2', [], False)]),
        ]), default_sync=True)

        non_sync_nodes = []
        for node in tree.browse_all_non_sync_nodes():
            non_sync_nodes.append(node.name)
            node.sync = True

        expected_non_sync_node = sorted(['A1', 'B', 'B2', 'C1', 'C2'])
        assert sorted(non_sync_nodes) == expected_non_sync_node

    def test_browse_skip_nodes_with_task(self):
        """Ensures browse_all_non_sync_nodes() never returns a node with task.

        When a node has a task associated, it must not be yielded by
        browse_all_non_sync_nodes(). Such a node must be skipped until there is
        no longer a task on it.
        """
        tree = IndexTree()
        tree._root = _make_tree(('root', [
            ('A', [('A1', [], False), ('A2',)]),
            ('B', [('B1',), ('B2', [], False)], False),
            ('C', [('C1', [], False), ('C2', [], False)]),
        ]), default_sync=True)

        tree._root.children['A'].children['A1'].task = True
        tree._root.children['B'].children['B1'].task = True
        tree._root.children['B'].children['B2'].task = True
        tree._root.children['C'].children['C2'].task = True

        non_sync_nodes = []
        for node in tree.browse_all_non_sync_nodes():
            if node is IndexTree.WAIT_FOR_TASK:
                break
            non_sync_nodes.append(node.name)
            node.sync = True

        expected_non_sync_node = sorted(['B', 'C1'])
        assert sorted(non_sync_nodes) == expected_non_sync_node

    def test_browse_until_all_is_clean(self):
        """browse must loop over all nodes many times until they're clean.

        A node non-sync can be yielded over and over again until it's synced.
        Then generator must stop only when all nodes are fully sync (when the
        whole tree is marked not dirty).
        """
        tree = IndexTree()
        tree._root = _make_tree(('node A', [('node B',)], True))
        node_a = tree._root
        node_b = tree._root.children['node B']
        # At start: A is sync, but not B

        gen = tree.browse_all_non_sync_nodes()

        # return node B until it's sync.
        non_sync_nodes = []
        for i in range(3):
            non_sync_nodes.append(next(gen))
        assert non_sync_nodes == [node_b, node_b, node_b]

        node_a.sync = False
        node_b.sync = True

        # return node A until it's sync.
        non_sync_nodes = []
        for i in range(3):
            non_sync_nodes.append(next(gen))
        assert non_sync_nodes == [node_a, node_a, node_a]

        node_b.sync = True

        # will yield until there is no remaining non-sync nodes.
        non_sync_nodes = []
        for i in range(15):
            non_sync_nodes.append(next(gen))
        assert len(non_sync_nodes) is 15

        node_a.sync = True
        node_b.sync = True

        # Tree is clean: Nothing to yield.
        assert len(list(gen)) is 0

    def test_browse_pauses_when_all_non_sync_nodes_have_task(self):
        """Check browse_all_non_sync_nodes() handles when all nodes have task.

        When all remaining nodes (meaning: non sync nodes) have a task
        associated, the generator has no node to return, but the iteration is
        not over.
        In this situation, it must return the special value
        `BROWSE_WAIT_FOR_TASK`.
        """
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)], True),
                                default_sync=False)
        tree._root.children['A'].task = True
        tree._root.children['B'].task = True

        gen = tree.browse_all_non_sync_nodes()

        # All nodes are reserved by tasks.
        assert next(gen) is IndexTree.WAIT_FOR_TASK
        assert next(gen) is IndexTree.WAIT_FOR_TASK

        tree._root.children['A'].task = None
        assert next(gen) is tree._root.children['A']
        tree._root.children['A'].sync = True
        assert next(gen) is IndexTree.WAIT_FOR_TASK

        tree._root.children['B'].sync = True
        # Although B is still reserved by a task, it's no longer dirty.
        assert next(gen, None) is None  # Iterator is empty


class TestGetNodeFromIndexTree(object):
    """Tests about node access methods of IndexTree."""

    def test_get_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A', [('A1',)]),
                                          ('B', [('B1',), ('B2',)])]))
        node_a1 = tree.get_node_by_path('A/A1')
        node_b = tree.get_node_by_path('B')
        assert node_a1 and node_a1.name == 'A1'
        assert node_b and node_b.name == 'B'

    def test_get_root_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        assert tree.get_node_by_path('.') is tree._root

    def test_get_missing_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        assert tree.get_node_by_path('A/ghost') is None

    def test_get_missing_root_node_by_path(self):
        tree = IndexTree()
        assert tree.get_node_by_path('.') is None

    def test_get_node_by_path_with_missing_folder(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        assert tree.get_node_by_path('A/B/C/ghost') is None

    def test_get_or_create_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A', [('A1',)]),
                                          ('B', [('B1',), ('B2',)])]))
        node_a1 = tree.get_or_create_node_by_path('A/A1', None)
        node_b = tree.get_or_create_node_by_path('B', None)
        assert node_a1 and node_a1.name == 'A1'
        assert node_b and node_b.name == 'B'

    def test_get_or_create_root_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        assert tree.get_or_create_node_by_path('.', None) is tree._root

    def test_get_or_create_missing_node_by_path(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        node = tree.get_or_create_node_by_path('A/ghost', MyNode)
        assert isinstance(node, MyNode)

    def test_get_or_create_node_by_path_without_root(self):
        tree = IndexTree()
        node = tree.get_or_create_node_by_path('A/b/c', MyNode)
        assert isinstance(node, MyNode)

    def test_get_or_create_node_by_path_with_missing_folder(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A',), ('B',)]))
        node = tree.get_or_create_node_by_path('A/B/C/ghost', MyNode)
        assert isinstance(node, MyNode)
