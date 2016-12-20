# -*- coding: utf-8 -*-

from bajoo.index.base_node import BaseNode


class TestBaseNode(object):

    def test_node_are_dirty_by_default(self):
        assert BaseNode('root').dirty
        assert not BaseNode('root').sync

    def test_node_parent_is_none_by_default(self):
        assert BaseNode('root').parent is None

    def test_node_are_not_removed_by_default(self):
        assert BaseNode('root').removed is False

    def test_add_child_on_empty_node(self):
        root = BaseNode('root')
        child = BaseNode('child')
        root.add_child(child)
        assert len(root.children) == 1
        assert root.children.get('child') is child

    def test_add_many_child(self):
        root = BaseNode('root')
        root.add_child(BaseNode('A'))
        root.add_child(BaseNode('B'))
        child_c = BaseNode('C')
        root.add_child(child_c)

        assert len(root.children) == 3
        assert root.children.get('C') is child_c

    def test_add_dirty_child_on_clean_tree(self):
        root = BaseNode('root')
        child_a = BaseNode('A')
        child_b = BaseNode('B')
        child_a_1 = BaseNode('A1')
        child_a_2 = BaseNode('A2')
        child_b_1 = BaseNode('B1')
        for node in (child_a, child_b):
            root.add_child(node)
        for node in (child_a_1, child_a_2):
            child_a.add_child(node)
        child_b.add_child(child_b_1)

        # set all nodes clean
        for node in (root, child_a, child_b, child_a_1, child_a_2, child_b_1):
            node._dirty = False
            node._sync = True

        dirty_child = BaseNode('dirty')
        child_a_2.add_child(dirty_child)

        assert all(node.dirty for node in
                   (dirty_child, child_a_2, child_a, root))
        assert all(not node.dirty for node in (child_a_1, child_b, child_b_1))
        assert all(node.sync for node in
                   (root, child_a, child_b, child_a_1, child_a_2, child_b_1))

    def test_add_child_set_parent(self):
        root = BaseNode('root')
        child = BaseNode('child')
        root.add_child(child)
        assert child.parent is root

    def test_set_node_not_sync(self):
        node = BaseNode('node')
        node._dirty = False
        node._sync = True

        node.sync = False
        assert node.dirty
        assert not node.sync

    def test_set_node_with_parent_as_not_sync(self):
        root = BaseNode('root')
        node = BaseNode('node')
        root.add_child(node)
        for n in (root, node):
            n._dirty = False
            n._sync = True

        node.sync = False
        assert not node.sync
        assert node.dirty
        assert root.sync
        assert root.dirty

    def test_set_empty_node_sync(self):
        node = BaseNode('node')

        node.sync = True
        assert not node.dirty
        assert node.sync

    def test_set_node_with_clean_children_sync(self):
        node = BaseNode('node')
        node.add_child(BaseNode('child 1'))
        node.add_child(BaseNode('child 2'))
        for child in node.children.values():
            child._dirty = False
            child._sync = True

        node.sync = True
        assert not node.dirty
        assert node.sync

    def set_node_with_dirty_children_sync(self):
        node = BaseNode('node')
        node.add_child(BaseNode('child 1'))
        node.add_child(BaseNode('child 2'))
        node.children['child 1']._dirty = True
        node.children['child 1']._sync = True

        assert node.dirty
        assert not node.sync
        node.sync = True
        assert node.dirty
        assert node.sync

    def test_rm_child(self):
        root = BaseNode('root')
        child_a = BaseNode('A')
        child_b = BaseNode('B')
        for node in (child_a, child_b):
            root.add_child(node)

        root.rm_child(child_a)
        assert child_a.parent is None
        assert child_a.removed is True
        assert child_a not in root.children

    def test_rm_dirty_child_updates_parent_flag(self):
        node = BaseNode('node')
        child1 = BaseNode('child 1')
        child2 = BaseNode('child 2')
        node.add_child(child1)
        node.add_child(child2)
        node.sync = True
        child1.sync = True
        child2.sync = False

        assert node.dirty
        node.rm_child(child2)
        assert not node.dirty

    def test_rm_child_propagate_removed_flag_to_all_children(self):
        root = BaseNode('root')
        node = BaseNode('node')
        child1 = BaseNode('child 1')
        child2 = BaseNode('child 2')
        root.add_child(node)
        node.add_child(child1)
        node.add_child(child2)

        for n in (root, node, child1, child2):
            assert n.removed is False
        root.rm_child(node)
        assert root.removed is False
        for n in (node, child1, child2):
            assert n.removed is True

    def test_node_remove_itself(self):
        root = BaseNode('root')
        child_a = BaseNode('A')
        child_b = BaseNode('B')
        for node in (child_a, child_b):
            root.add_child(node)

        child_a.remove_itself()
        assert child_a.parent is None
        assert child_a.removed is True
        assert child_a not in root.children

    def test_dirty_node_removing_itself_updates_parent_flag(self):
        node = BaseNode('node')
        child1 = BaseNode('child 1')
        child2 = BaseNode('child 2')
        node.add_child(child1)
        node.add_child(child2)
        node.sync = True
        child1.sync = True
        child2.sync = False

        assert node.dirty
        child2.remove_itself()
        assert not node.dirty

    def test_remove_itself_propagate_removed_flag_to_all_children(self):
        root = BaseNode('root')
        node = BaseNode('node')
        child1 = BaseNode('child 1')
        child2 = BaseNode('child 2')
        root.add_child(node)
        node.add_child(child1)
        node.add_child(child2)

        for n in (root, node, child1, child2):
            assert n.removed is False
        node.remove_itself()
        assert root.removed is False
        for n in (node, child1, child2):
            assert n.removed is True

    def test_set_hierarchy_not_sync(self):
        node = BaseNode('node')
        child1 = BaseNode('child 1')
        child2 = BaseNode('child 2')
        node.add_child(child1)
        node.add_child(child2)
        node.sync = True
        child1.sync = True
        child2.sync = True

        node.set_all_hierarchy_not_sync()
        assert node.sync is False
        assert child1.sync is False
        assert child2.sync is False

    def test_get_full_path_on_root_node(self):
        node = BaseNode(u'root')
        assert node.get_full_path() == u'.'

    def test_get_full_path_on_first_level_node(self):
        node = BaseNode(u'node')
        child1 = BaseNode(u'child 1')
        child2 = BaseNode(u'child 2')
        node.add_child(child1)
        node.add_child(child2)

        assert child1.get_full_path() == 'child 1'
        assert child2.get_full_path() == 'child 2'

    def test_get_full_path_on_nested_nodes(self):
        node = BaseNode(u'root')
        node_a = BaseNode(u'A')
        node_b = BaseNode(u'B')
        node_c = BaseNode(u'C')
        node.add_child(node_a)
        node_a.add_child(node_b)
        node_b.add_child(node_c)

        assert node_c.get_full_path() == u'A/B/C'

    def test_release_method_set_task_to_none(self):
        node = BaseNode(u'root')
        node.task = 'X'
        node.release()
        assert node.task is None

    def test_release_method_set_node_as_sync_if_node_has_no_hint(self):
        node = BaseNode(u'root')
        node.state = {'exists': True}
        node.task = 'X'
        node.release()
        assert node.sync is True

    def test_release_method_let_node_non_sync_if_node_has_hint(self):
        node = BaseNode(u'root')
        node.state = {'exists': True}
        node.task = 'X'
        node.local_hint = "HINT"
        node.release()
        assert node.sync is False

    def test_release_method_remove_node_from_tree_when_state_is_none(self):
        root = BaseNode(u'root')
        folder = BaseNode(u'folder')
        child = BaseNode(u'child')
        child.task = 'X'
        root.add_child(folder)
        folder.add_child(child)

        child.release()
        assert child.parent is None
        assert len(folder.children) is 0

    def test_release_method_dont_remove_node_when_children_exists(self):
        root = BaseNode(u'root')
        child = BaseNode(u'child')
        child.task = 'X'
        child.add_child(BaseNode(u'X'))
        root.add_child(child)

        child.release()
        assert child.parent is root

    def test_release_method_dont_remove_node_if_hint_exists(self):
        root = BaseNode(u'root')
        folder = BaseNode(u'folder')
        child = BaseNode(u'child')
        child.task = 'X'
        child.local_hint = "HINT"
        root.add_child(folder)
        folder.add_child(child)

        child.release()
        assert child.parent is folder

    def test_release_method_set_empty_parent_dirty_after_removal(self):
        root = BaseNode(u'root')
        folder = BaseNode(u'folder')
        folder.sync = True
        child = BaseNode(u'child')
        child.task = 'X'
        root.add_child(folder)
        folder.add_child(child)

        child.release()
        assert folder.sync is False

    def test_release_method_leave_non_empty_parent_intact_after_removal(self):
        root = BaseNode(u'root')
        folder = BaseNode(u'folder')
        folder.sync = True
        child = BaseNode(u'child')
        child.task = 'X'
        root.add_child(folder)
        folder.add_child(child)
        folder.add_child(BaseNode(u'other child'))

        child.release()
        assert folder.sync is True
