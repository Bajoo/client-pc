# -*- coding: utf-8 -*-

import threading
from bajoo.index.hints import (DeletedHint, DestMoveHint, ModifiedHint,
                               SourceMoveHint)
from bajoo.index.hint_builder import HintBuilder


class FakeNode(object):
    def __init__(self, name, exists=False, local_state=None,
                 remote_state=None):
        self.name = name
        self.local_hint = None
        self.remote_hint = remote_state
        self.task = None
        self.local_state = local_state
        self.remote_state = None
        self._exists = exists

        self.tree = None

    def exists(self):
        return self._exists

    def remove_itself(self):
        for key, node in self.tree.nodes.items():
            if node is self:
                del self.tree.nodes[key]
                break


class FakeIndexTree(object):
    def __init__(self, nodes={}):
        self.lock = threading.Lock()
        self.nodes = {}

        for path, node in nodes.items():
            node.tree = self
            node._exists = True
            self.nodes[path] = node

    def get_node_by_path(self, path):
        return self.nodes.get(path)

    def get_or_create_node_by_path(self, path, factory):
        try:
            return self.nodes[path]
        except KeyError:
            self.nodes[path] = factory(path.split('/')[-1])
            self.nodes[path].tree = self
            return self.nodes[path]


class TestHintBuilder(object):
    """Test of the IndexTree.browse_all_non_sync_nodes() method."""

    def test_modification_event_on_empty_node(self):
        """Should add the ModifiedHint."""
        builder = HintBuilder()
        node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'NEW STATE', FakeNode)
        assert isinstance(node.local_hint, ModifiedHint)
        assert node.local_hint.new_data == 'NEW STATE'
        assert node.remote_hint is None

    def test_deletion_event_on_empty_node(self):
        """Should add the DeletedHint."""
        builder = HintBuilder()
        node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_deleted_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C')
        assert isinstance(node.remote_hint, DeletedHint)
        assert node.local_hint is None

    def test_move_event_from_empty_node(self):
        """Should add the SourceMoveHint, then create a destination node."""

        builder = HintBuilder()
        src_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': src_node
        })

        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)

        assert isinstance(src_node.remote_hint, SourceMoveHint)
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.remote_hint, DestMoveHint)
        assert src_node.remote_hint.dest_node is dest_node
        assert dest_node.remote_hint.source_node is src_node

    def test_modification_event_on_missing_node(self):
        """Should create a new node."""
        tree = FakeIndexTree()
        builder = HintBuilder()

        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'NEW STATE', FakeNode)

        node = tree.get_node_by_path('A/B/C')
        assert isinstance(node.local_hint, ModifiedHint)
        assert node.local_hint.new_data == 'NEW STATE'
        assert node.remote_hint is None

    def test_deletion_on_missing_node(self):
        """Deletion should do nothing if the file don't exists."""
        tree = FakeIndexTree()
        builder = HintBuilder()

        builder.apply_deleted_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C')

        assert tree.get_node_by_path('A/B/C') is None

    def test_move_missing_node(self):
        """The destination node's hint should be "Modified"

        This is an unusual case that should not happens.
        We can't set the "move" hints, as the previous information are not
        reliable. The source node will remains missing, and the destination
        node's hint will be set to "Modified".
        """
        tree = FakeIndexTree()
        builder = HintBuilder()

        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                 'D/E/F', FakeNode)

        assert tree.get_node_by_path('A/B/C') is None
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.local_hint, ModifiedHint)
        assert dest_node.local_hint.new_data is None

    def test_modification_event_on_modified_node(self):
        """Should Replace the first modification."""
        builder = HintBuilder()
        node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_modified_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                     'STATE 1', FakeNode)
        builder.apply_modified_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                     'STATE 2', FakeNode)

        assert isinstance(node.remote_hint, ModifiedHint)
        assert node.remote_hint.new_data == 'STATE 2'
        assert node.local_hint is None

    def test_modification_event_on_deleted_node(self):
        """Should replace the deleted event."""
        builder = HintBuilder()
        node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_deleted_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C')
        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'STATE', FakeNode)

        assert isinstance(node.local_hint, ModifiedHint)
        assert node.local_hint.new_data == 'STATE'

    def test_modification_event_on_moved_src_node(self):
        """Should rewrite both move hints.

        The source hint should be replaced by the new ModifiedHint. The
        destination node's hint should be converted in a ModifiedHint.
        There is too much changes to use the "move" information, as we don't
        have the source.
        """
        builder = HintBuilder()
        node = FakeNode('C', local_state='INITIAL STATE')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                 'D/E/F', FakeNode)
        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'STATE', FakeNode)

        assert isinstance(node.local_hint, ModifiedHint)
        assert node.local_hint.new_data == 'STATE'
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.local_hint, ModifiedHint)
        assert dest_node.local_hint.new_data == 'INITIAL STATE'

    def test_modification_event_on_moved_dst_node(self):
        """Should rewrite both move hints.

        The destination node's hint is replaced by the new one. The source
        node has moved, which is equivalent to a deletion.
        """
        builder = HintBuilder()
        source_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': source_node
        })

        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)
        builder.apply_modified_event(tree, HintBuilder.SCOPE_REMOTE, 'D/E/F',
                                     'STATE', FakeNode)

        assert isinstance(source_node.remote_hint, DeletedHint)
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.remote_hint, ModifiedHint)
        assert dest_node.remote_hint.new_data == 'STATE'

    def test_deletion_event_on_modified_node(self):
        """It should delete the node anyway."""
        builder = HintBuilder()
        node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': node
        })

        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'STATE', FakeNode)
        builder.apply_deleted_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C')

        assert isinstance(node.local_hint, DeletedHint)

    def test_deletion_event_on_new_node_should_remote_it(self):
        tree = FakeIndexTree()
        builder = HintBuilder()

        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C',
                                     'NEW STATE', FakeNode)
        builder.apply_deleted_event(tree, HintBuilder.SCOPE_LOCAL, 'A/B/C')

        assert tree.get_node_by_path('A/B/C') is None

    def test_deletion_event_on_moved_src_node(self):
        """It should do nothing.

        The target has moved: it's already gone, there is nothing to delete.
        """
        builder = HintBuilder()
        source_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': source_node
        })

        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)
        builder.apply_deleted_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C')

        assert isinstance(source_node.remote_hint, SourceMoveHint)
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.remote_hint, DestMoveHint)

    def test_deletion_event_on_moved_dest_node(self):
        """Should mark both node as deleted.

        After the move, the source node don't point to something anymore.
        After the delete, the destination node is also gone: both node should
        have a "deleted" hint.
        If the destination didn't exist before the move, the node should be
        removed.
        """
        builder = HintBuilder()
        source_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': source_node
        })

        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)
        builder.apply_deleted_event(tree, HintBuilder.SCOPE_REMOTE, 'D/E/F')

        assert isinstance(source_node.remote_hint, DeletedHint)
        assert tree.get_node_by_path('D/E/F') is None

    def test_move_event_from_modified_node(self):
        """It should do the move with "Deleted" and "Modified" hints.

        The source node should be "Deleted". The destination node should be
        "Modified", and should keep the data the source node had before the
        move.
        """
        builder = HintBuilder()
        src_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': src_node
        })

        builder.apply_modified_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                     'NEW STATE', FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)

        assert isinstance(src_node.remote_hint, DeletedHint)
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.remote_hint, ModifiedHint)
        assert dest_node.remote_hint.new_data == 'NEW STATE'

    def test_move_event_from_deleted_node(self):
        """It should set a "Modified" hint for destination node.

        This is a unusual case: the source can't be moved if it's been deleted
        before. As we can't know what happened, the destination node's hint
        will be "Modified", without state. The source node's hint is "Deleted"
        anyway.
        """
        builder = HintBuilder()
        src_node = FakeNode('C', remote_state='STATE?')
        tree = FakeIndexTree({
            'A/B/C': src_node
        })

        builder.apply_deleted_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C')
        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)

        assert isinstance(src_node.remote_hint, DeletedHint)
        dest_node = tree.get_node_by_path('D/E/F')
        assert isinstance(dest_node.remote_hint, ModifiedHint)
        assert dest_node.remote_hint.new_data is None

    def test_move_event_from_already_moved_node(self):
        """It should split the move in "Deleted" and "Modified" hints.

        This is a unusual case: the source can't be moved twice.
        We can't be sure the source was correct: We set a "Modified" hint
        without new state to the destination node.
        """
        builder = HintBuilder()
        src_node = FakeNode('C')
        tree = FakeIndexTree({
            'A/B/C': src_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'D/E/F', FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_REMOTE, 'A/B/C',
                                 'G/H/I', FakeNode)

        first_dest_node = tree.get_node_by_path('D/E/F')
        second_dest_node = tree.get_node_by_path('G/H/I')
        assert isinstance(src_node.remote_hint, DeletedHint)
        assert isinstance(first_dest_node.remote_hint, ModifiedHint)
        assert isinstance(second_dest_node.remote_hint, ModifiedHint)
        assert second_dest_node.remote_hint.new_data is None

    def test_move_event_from_previous_move_dest(self):
        """It should chain the two move.

        If A move to B, then B move to C:
        - It equivalents of a move from A to C
        - B is deleted during the operation.
        """
        builder = HintBuilder()
        src_node = FakeNode('A')
        tree = FakeIndexTree({
            'A': src_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'B', 'C',
                                 FakeNode)

        assert tree.get_node_by_path('B') is None
        dest_node = tree.get_node_by_path('C')
        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert src_node.local_hint.dest_node is dest_node
        assert dest_node.local_hint.source_node is src_node

    def test_two_opposite_event_moves(self):
        """source node shouldn't changes, and dest node should be deleted.

        If there is two moves "A -> B", then "B -> A",
        The source node shouldn't change. The destination node (B) should be
        destroyed in the operation.
        """
        builder = HintBuilder()
        src_node = FakeNode('A')
        tree = FakeIndexTree({
            'A': src_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'B', 'A',
                                 FakeNode)

        assert tree.get_node_by_path('B') is None
        assert src_node.local_hint is None

    def test_move_event_to_existing_node(self):
        """It should replace the destination node."""
        builder = HintBuilder()
        src_node = FakeNode('A')
        dest_node = FakeNode('B')
        tree = FakeIndexTree({
            'A': src_node,
            'B': dest_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)

        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert dest_node.local_hint.source_node is src_node
        assert src_node.local_hint.dest_node is dest_node

    def test_move_event_to_existing_modified_node(self):
        """It should replace the destination node."""
        builder = HintBuilder()
        src_node = FakeNode('A')
        dest_node = FakeNode('B')
        tree = FakeIndexTree({
            'A': src_node,
            'B': dest_node
        })
        builder.apply_modified_event(tree, HintBuilder.SCOPE_LOCAL, 'B',
                                     'state', FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)

        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert dest_node.local_hint.source_node is src_node
        assert src_node.local_hint.dest_node is dest_node

    def test_move_event_to_existing_deleted_node(self):
        """It should replace the destination node."""
        builder = HintBuilder()
        src_node = FakeNode('A')
        dest_node = FakeNode('B')
        tree = FakeIndexTree({
            'A': src_node,
            'B': dest_node
        })
        builder.apply_deleted_event(tree, HintBuilder.SCOPE_LOCAL, 'B')
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)

        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert dest_node.local_hint.source_node is src_node
        assert src_node.local_hint.dest_node is dest_node

    def test_move_event_to_existing_moved_source_node(self):
        """It should replace the destination node, but "split" the first move.

        There is two moves B -> C, then A -> B.
        The second move will replace the node B (and so, node A's hint will be
        a "SourceMoveHint", and node B's hint will be a "DestMoveHint").
        However, the node C's hint, originally a "DestMoveHint", must be
        replaced by a "ModifiedHint".
        """
        builder = HintBuilder()
        src_node = FakeNode('A')
        dest_node = FakeNode('B', local_state='INITIAL B STATE')
        tree = FakeIndexTree({
            'A': src_node,
            'B': dest_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'B', 'C',
                                 FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'B',
                                 FakeNode)

        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert dest_node.local_hint.source_node is src_node
        assert src_node.local_hint.dest_node is dest_node

        first_dest_node = tree.get_node_by_path('C')
        assert isinstance(first_dest_node.local_hint, ModifiedHint)
        assert first_dest_node.local_hint.new_data == 'INITIAL B STATE'

    def test_move_event_to_existing_moved_destination_node(self):
        """It should replace the destination node, but "split" the first move.

        There is two moves B -> C, then A -> C.
        The second move will replace the node C (and so, node A's hint will be
        a "SourceMoveHint", and node C's hint will be a "DestMoveHint").
        However, the node B's hint, originally a "SourceMoveHint", must be
        replaced by a "DeletedHint".
        """
        builder = HintBuilder()
        src_node = FakeNode('A')
        first_source_node = FakeNode('B')
        tree = FakeIndexTree({
            'A': src_node,
            'B': first_source_node
        })
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'B', 'C',
                                 FakeNode)
        builder.apply_move_event(tree, HintBuilder.SCOPE_LOCAL, 'A', 'C',
                                 FakeNode)

        dest_node = tree.get_node_by_path('C')
        assert isinstance(src_node.local_hint, SourceMoveHint)
        assert isinstance(dest_node.local_hint, DestMoveHint)
        assert dest_node.local_hint.source_node is src_node
        assert src_node.local_hint.dest_node is dest_node

        assert isinstance(first_source_node.local_hint, DeletedHint)
