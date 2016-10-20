# -*- coding: utf-8 -*-

from bajoo.index.base_node import BaseNode


class TestBaseNode(object):

    def test_node_are_dirty_by_default(self):
        assert BaseNode('root').dirty
        assert not BaseNode('root').sync

    def test_node_parent_is_none_by_default(self):
        assert BaseNode('root').parent is None

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

    def test_node_remove_itself(self):
        root = BaseNode('root')
        child_a = BaseNode('A')
        child_b = BaseNode('B')
        for node in (child_a, child_b):
            root.add_child(node)

        child_a.remove_itself()
        assert child_a.parent is None
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
