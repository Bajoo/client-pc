# -*- coding: utf-8 -*-

from bajoo.common.fs import hide_file_if_windows
from bajoo.filesync.folder_task import FolderTask
from bajoo.index.hints import DeletedHint, ModifiedHint
from bajoo.index.file_node import FileNode
from bajoo.index.folder_node import FolderNode


class FakeFolderNode(object):
    def __init__(self, name=u'node', full_path=u'node', exists=True):
        self.full_path = full_path
        self.name = name
        self.state = None
        self.local_hint = None
        self.remote_hint = None
        self.sync = False
        self.dirty = False
        self.children = {}
        self.is_released = False
        self._exists = exists

    def get_full_path(self):
        return self.full_path

    def set_state(self, value):
        self.state = value

    def release(self):
        self.is_released = True

    def exists(self):
        return self._exists

    def add_child(self, child):
        self.children[child.name] = child

    def check(self, **kwargs):
        """Generic check method to assert value of node attributes."""
        for key, value in kwargs.items():
            assert getattr(self, key) == value

    def undeleted_children(self):
        """Returns children that have no Deleted hint."""
        return list(child for child in self.children.values()
                    if not isinstance(child.local_hint, DeletedHint))


class TestFolderTask(object):

    def test_execute_check_on_existing_folder(self, tmpdir):
        node = FakeFolderNode()
        tmpdir.mkdir(node.name).join('file').write('content')

        result = FolderTask.execute(tmpdir.strpath, node, None)
        assert result == (['file'], [])

    def test_execute_check_on_missing_folder(self, tmpdir):
        node = FakeFolderNode()
        result = FolderTask.execute(tmpdir.strpath, node, None)
        assert result == ([], [])

    def test_execute_on_empty_folder_should_remove_it(self, tmpdir):
        """When a folder is fully empty, it should be deleted."""
        node = FakeFolderNode(exists=False)
        tmpdir.mkdir(node.name)
        result = FolderTask.execute(tmpdir.strpath, node, None)
        assert not tmpdir.join(node.name).exists()
        assert result == ([], [])

    def test_execute_should_keep_newly_created_empty_folder(self, tmpdir):
        """When an empty folder is created, it shouldn't be deleted.

        execute() should delete empty folders, unless the folder has just been
        created. When such case occurs, the folder has a local hint "Modified".
        """
        node = FakeFolderNode(exists=False)
        tmpdir.mkdir(node.name)
        result = FolderTask.execute(tmpdir.strpath, node, ModifiedHint())
        assert tmpdir.join(node.name).exists()
        assert result == ([], [])

    def test_list_dir_on_non_existent_folder(self, tmpdir):
        result = FolderTask.list_dir(tmpdir.strpath, 'not exists', None)
        assert result == ([], [])

    def test_list_dir_on_empty_folder(self, tmpdir):
        tmpdir.mkdir('target_dir')
        result = FolderTask.list_dir(tmpdir.strpath, 'target_dir', None)
        assert result == ([], [])

    def test_list_dir_on_folder_with_file(self, tmpdir):
        tmpdir.mkdir('target_dir').join('file').write('File content')
        result = FolderTask.list_dir(tmpdir.strpath, 'target_dir', None)
        assert result == (['file'], [])

    def test_list_dir_on_folder_with_subfolder(self, tmpdir):
        tmpdir.mkdir('target_dir').mkdir('subfolder')
        result = FolderTask.list_dir(tmpdir.strpath, 'target_dir', None)
        assert result == ([], ['subfolder'])

    def test_list_dir_on_folder_with_hidden_file(self, tmpdir):
        """Hidden files must be ignored, only if the config says so."""
        hidden_file = tmpdir.mkdir('target_dir').join('.hidden_file')
        hide_file_if_windows(hidden_file.strpath)
        result = FolderTask.list_dir(tmpdir.strpath, 'target_dir', None)
        assert result == ([], [])

    def test_list_dir_on_folder_with_bajoo_index(self, tmpdir):
        """Index files must be ignored by the list dir."""
        tmpdir.mkdir('target_dir').join('.bajoo-special_file')
        result = FolderTask.list_dir(tmpdir.strpath, 'target_dir', None)
        assert result == ([], [])

    def test_apply_result_set_new_state(self):
        node = FakeFolderNode()
        FolderTask.diff_node_and_apply_result(node, {'new': 'state'}, [], [])
        node.check(state={'new': 'state'})

    def test_apply_result_set_state_none(self):
        node = FakeFolderNode()
        FolderTask.diff_node_and_apply_result(node, None, [], [])
        node.check(state=None)

    def test_apply_empty_list_on_empty_node(self):
        """Execute diff+apply with empty child lists, on node without child."""
        node = FakeFolderNode()
        FolderTask.diff_node_and_apply_result(node, None, [], [])

        assert len(node.children) is 0

    def test_apply_empty_list_on_node_with_child(self):
        """Execute diff+apply with empty child lists, on node with child."""
        node = FakeFolderNode()
        for name in ('A', 'B', 'C'):
            node.children[name] = FakeFolderNode(name)
        FolderTask.diff_node_and_apply_result(node, None, [], [])
        assert len(node.undeleted_children()) is 0

    def test_apply_new_folder_on_empty_list(self):
        """Execute diff+apply with not empty folder list on empty node."""
        node = FakeFolderNode()
        FolderTask.diff_node_and_apply_result(node, None, [u'new file'], [])

        assert len(node.undeleted_children()) is 1
        assert isinstance(node.children[u'new file'], FileNode)

    def test_apply_new_file_on_empty_list(self):
        """Execute diff+apply with not empty file list on empty node."""
        node = FakeFolderNode()
        FolderTask.diff_node_and_apply_result(node, None, [], [u'new folder'])

        assert len(node.undeleted_children()) is 1
        assert isinstance(node.children[u'new folder'], FolderNode)

    def test_diff_and_apply_no_change_on_node_with_child(self):
        """Execute diff+apply with the nodes already present in the node."""
        node = FakeFolderNode()
        for name in ('A', 'B', 'C'):
            node.children[name] = FakeFolderNode(name)
        FolderTask.diff_node_and_apply_result(node, None, ['A', 'B'], ['C'])
        assert len(node.undeleted_children()) is 3
