# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from bajoo.index.base_node import BaseNode
from bajoo.index.new_index_tree import IndexTree
from bajoo.index.file_node import FileNode
from bajoo.index.folder_node import FolderNode


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

    def test_set_tree_node_sync(self):
        tree = IndexTree()
        tree._root = _make_tree(('root', [('A', [('A1',)]),
                                          ('B', [('B1',), ('B2',)])]))
        tree.set_tree_not_sync()
        assert tree._root.sync is False
        assert tree._root.children['A'].sync is False
        assert tree._root.children['B'].sync is False
        assert tree._root.children['A'].children['A1'].sync is False
        assert tree._root.children['B'].children['B1'].sync is False
        assert tree._root.children['B'].children['B2'].sync is False

    def test_set_empty_tree_node_not_sync(self):
        tree = IndexTree()
        # should do nothing
        tree.set_tree_not_sync()


class TestSaveAndLoadIndexTree(object):

    def test_load_from_legacy_empty_tree(self):
        tree = IndexTree()
        tree.load({})
        assert tree._root is None

    def test_load_from_legacy_flat_tree(self):
        tree = IndexTree()
        tree.load({
            u'file1': ('hash1', 'hash2'),
            u'file2': ('hash3', None),
            u'file3': ('hash4', None),
            u'file4': (None, None)
        })
        assert tree._root is not None
        for path in ('file1', 'file2', 'file3', 'file4'):
            assert isinstance(tree.get_node_by_path(path), FileNode)
        assert tree.get_node_by_path('file5') is None

    def test_load_from_legacy_nested_tree(self):
        tree = IndexTree()
        tree.load({
            u'deep/nested/file': ('123546', 'abcdef')
        })
        assert tree._root is not None
        assert isinstance(tree.get_node_by_path('deep/nested'), FolderNode)
        assert isinstance(tree.get_node_by_path('deep/nested/file'), FileNode)

    def test_load_from_legacy_should_correctly_set_hashes(self):
        tree = IndexTree()
        tree.load({
            u'root_file': ('3f4855158eb3266a74cf3a5d78b361cc',
                           '1e4c2746ef98ebb5fe703723ecc3b8fd'),
            u'nested/file': ('148fff4717a87b8ddacb8a4b1fd18531',
                             '02d70d1f6d522c454883d6114c7f315f')
        })
        assert tree._root is not None
        root_file = tree.get_node_by_path('root_file')
        assert root_file.state == {
            'local_hash': '3f4855158eb3266a74cf3a5d78b361cc',
            'remote_hash': '1e4c2746ef98ebb5fe703723ecc3b8fd'}
        nested_file = tree.get_node_by_path('nested/file')
        assert nested_file.state == {
            'local_hash': '148fff4717a87b8ddacb8a4b1fd18531',
            'remote_hash': '02d70d1f6d522c454883d6114c7f315f'}

    def test_root_node_should_be_named_dot_after_load(self):
        tree = IndexTree()
        tree.load({
            'version': 2,
            'root': {
                'type': 'FOLDER',
                'state': None,
            }
        })
        assert tree._root is not None
        assert tree._root.name == u'.'

    def test_root_node_should_be_named_dot_after_legacy_load(self):
        tree = IndexTree()
        tree.load({u'x': (None, None)})
        assert tree._root is not None
        assert tree._root.name == u'.'

    def test_load_tree_should_set_default_state_to_none(self):
        tree = IndexTree()
        tree.load({
            'version': 2,
            'root': {
                'type': 'FOLDER',
            }
        })
        assert tree._root.state is None

    def test_load_tree_should_set_all_node_names(self):
        tree = IndexTree()
        tree.load({
            'version': 2,
            'root': {
                'type': "FOLDER",
                'children': {
                    u'file1': {
                        'type': "FILE",
                        'state': {'local_hash': 'hash1',
                                  'remote_hash': 'hash2'}
                    },
                    u'file2': {
                        'type': "FILE",
                        'state': {'local_hash': 'hash3',
                                  'remote_hash': 'hash4'},
                    },
                    u'file3': {
                        'type': "FILE",
                        'state': {'local_hash': 'hash5',
                                  'remote_hash': 'hash6'}
                    },
                    u'file4': {'type': "FILE"},
                    u'nested': {
                        'type': "FOLDER",
                        'children': {
                            u'child.txt': {
                                'type': "FILE",
                            }
                        }
                    }
                }
            }
        })
        assert tree._root is not None
        for path in ('file1', 'file2', 'file3', 'file4'):
            node = tree.get_node_by_path(path)
            assert node.name == path
        node = tree.get_node_by_path('nested/child.txt')
        assert node.name == 'child.txt'

    def test_export_index_should_be_informat_version_2(self):
        tree = IndexTree()
        data = tree.export_data()
        assert data.get('version') == 2

    def test_export_index_tree_without_root_node(self):
        tree = IndexTree()
        data = tree.export_data()
        assert data.get('version') == 2

    def test_export_index_tree_with_only_root_node(self):
        tree = IndexTree()
        tree._root = FolderNode('.')
        data = tree.export_data()
        root_def = data.get('root')
        assert root_def['type'] == "FOLDER"
        assert len(root_def.get('children', {})) == 0

    def test_export_index_tree_with_nested_nodes(self):
        tree = IndexTree()
        tree._root = FolderNode('.')
        tree._root.add_child(FolderNode('A'))
        tree._root.children['A'].add_child(FileNode('A1'))
        tree._root.children['A'].add_child(FolderNode('A2'))
        tree._root.add_child(FolderNode('B'))
        tree._root.children['B'].add_child(FileNode('B1'))

        data = tree.export_data()
        assert data['root']['type'] == "FOLDER"
        node_a_def = data['root']['children']['A']
        node_b_def = data['root']['children']['B']
        assert node_a_def['type'] == "FOLDER"
        assert node_b_def['type'] == "FOLDER"
        assert node_a_def['children']['A1']['type'] == "FILE"
        assert node_a_def['children']['A2']['type'] == "FOLDER"
        assert node_b_def['children']['B1']['type'] == "FILE"

    def test_export_index_tree_returns_states(self):
        tree = IndexTree()
        tree._root = FolderNode('.')
        node_folder = FolderNode('folder')
        node_child = FileNode('child')
        tree._root.add_child(node_folder)
        node_folder.add_child(node_child)

        tree._root.state = {'local_hash': 1, 'remote_hash': 2}
        node_folder.state = {'local_hash': 3, 'remote_hash': 4}
        node_child.state = {'local_hash': 5, 'remote_hash': 6}

        data = tree.export_data()
        root_node_def = data['root']
        assert root_node_def['state'] == {'local_hash': 1, 'remote_hash': 2}
        folder_node_def = root_node_def['children']['folder']
        assert folder_node_def['state'] == {'local_hash': 3, 'remote_hash': 4}
        child_node_def = folder_node_def['children']['child']
        assert child_node_def['state'] == {'local_hash': 5, 'remote_hash': 6}


class TestIndexTree(object):
    """Other IndexTree tests who doesn't fit in other classes."""

    def test_get_remote_hash_of_empty_tree(self):
        tree = IndexTree()
        assert tree.get_remote_hashes() == {}

    def test_get_remote_hash_of_tree_containing_only_folders(self):
        tree = IndexTree()
        tree._root = FolderNode('.')
        node_folder = FolderNode('folder')
        tree._root.add_child(node_folder)
        node_folder.add_child(FolderNode('nested folder'))

        assert tree.get_remote_hashes() == {}

    def test_get_remote_hash_of_tree_with_files(self):
        tree = IndexTree()
        file_a1 = FileNode('A1')
        file_a1.state = {'local_hash': 'abcd', 'remote_hash': 1234}
        file_b1 = FileNode('B1')
        file_b1.state = {'local_hash': 'ef01', 'remote_hash': 5678}

        tree._root = FolderNode('.')
        tree._root.add_child(FolderNode('A'))
        tree._root.children['A'].add_child(file_a1)
        tree._root.children['A'].add_child(FolderNode('A2'))
        tree._root.add_child(FolderNode('B'))
        tree._root.children['B'].add_child(file_b1)

        data = tree.get_remote_hashes()
        assert data == {
            u'A/A1': 1234,
            u'B/B1': 5678,
        }
