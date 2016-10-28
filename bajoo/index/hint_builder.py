
import logging
from .hints import DeletedHint, DestMoveHint, ModifiedHint, SourceMoveHint

_logger = logging.getLogger(__name__)


class HintBuilder(object):
    """Build and set hint attributes on index node, from external event.

    The Builder is a class dedicated to convert external event
    (creation/modification, deletion and move) in hint, and to apply them to
    the nodes.
    It handles all specific cases when many events occurs on the same node, and
    it merges the hints to keep a coherent state.
    """

    # TODO: handle case when there is conflict between node of different types
    # (files and folders)

    EVENT_MODIFIED = 'modified'
    EVENT_DELETED = 'deleted'
    EVENT_MOVE = 'move'

    SCOPE_LOCAL = 'local'
    SCOPE_REMOTE = 'remote'

    @classmethod
    def _get_hint(cls, node, scope):
        if scope is cls.SCOPE_LOCAL:
            return node.local_hint
        else:
            return node.remote_hint

    @classmethod
    def _set_hint(cls, node, scope, hint):
        if scope is cls.SCOPE_LOCAL:
            node.local_hint = hint
        else:
            node.remote_hint = hint

    @classmethod
    def _get_state(cls, node, scope):
        if scope is cls.SCOPE_LOCAL:
            return node.local_state
        else:
            return node.remote_state

    def _set_delete_hint(self, node, scope):
        """Set a DeletedHint(), or directly delete the node when possible.

        In some case, a node can be removed from the tree when two hints have
        no effect together (eg: the creation of a file, followed by it's
        deletion). In these cases, the node itself can be deleted, as a task on
        it would only remove the node.
        This method detects theses cases and delete the node.

        In other cases, it act like a call to:
            `_set_hint(node, scope, DeletedHint())`.
        """
        if not node.exists():
            if scope == self.SCOPE_REMOTE:
                other_scope = self.SCOPE_LOCAL
            else:
                other_scope = self.SCOPE_REMOTE
            hint = self._get_hint(node, other_scope)
            if hint is None or isinstance(hint, DeletedHint):
                # No need to action: the entire node can be deleted safely.
                node.remove_itself()
                return

        self._set_hint(node, scope, DeletedHint())

    def _set_move_hints(self, scope, source_node, dest_node):
        """Set both hints needed to indicate a move between two nodes.

        Args:
            scope (str):
            source_node (BaseNode): source node
            dest_node (BaseNode): destination node
        """
        self._set_hint(source_node, scope, SourceMoveHint(dest_node))
        self._set_hint(dest_node, scope, DestMoveHint(source_node))

    def apply_modified_event(self, tree, scope, path, new_state, node_factory):
        """Create or update hint from a MODIFIED or an ADDED event.

        Args:
            tree (IndexTree): index of concerned node.
            scope (str): One of SCOPE_LOCAL or SCOPE_REMOTE.
            path (Text): path of the added/modified element.
            new_state (Optional[Any]): data representing the node state of
                the node. state's type is dependent of the node's type.
            node_factory (Callable[[Text], BaseNode]): function used to create
                the node, if needed. It receives the node's name in argument
                and must return a single node.
        """

        with tree.lock:
            node = tree.get_or_create_node_by_path(path, node_factory)
            node.sync = False
            previous_hint = self._get_hint(node, scope)

            if isinstance(previous_hint,
                          (type(None), DeletedHint, ModifiedHint)):
                self._set_hint(node, scope, ModifiedHint(new_state))
            elif isinstance(previous_hint, SourceMoveHint):
                # If we've a 'MOVE' event, we're sure the source state is the
                # new state of the destination node.
                origin_state = self._get_state(node, scope)
                self._set_hint(previous_hint.dest_node, scope,
                               ModifiedHint(origin_state))
                self._set_hint(node, scope, ModifiedHint(new_state))
            elif isinstance(previous_hint, DestMoveHint):
                self._set_delete_hint(previous_hint.source_node, scope)
                self._set_hint(node, scope, ModifiedHint(new_state))

    def apply_deleted_event(self, tree, scope, path):
        """Create or update hint from a DELETED event.

        Args:
            tree (IndexTree): index of concerned node.
            scope (str): One of SCOPE_LOCAL or SCOPE_REMOTE.
            path (Text): path of the deleted element.
        """
        with tree.lock:
            node = tree.get_node_by_path(path)
            if node is None:
                return  # Nothing to do: the node don't exists.

            node.sync = False
            previous_hint = self._get_hint(node, scope)

            if isinstance(previous_hint, SourceMoveHint):
                # This case shouldn't happens (deletion of an object that is
                # not here). Anyway, the file is already gone
                # (move elsewhere). Nothing to do.
                _logger.warning('Weird deletion event for a moved node. '
                                'Path is %s', path)
                return

            self._set_delete_hint(node, scope)

            if isinstance(previous_hint, DestMoveHint):
                # Delete the source move. We've already deleted the destination
                self._set_delete_hint(previous_hint.source_node, scope)

    def apply_move_event(self, tree, scope, src_path, dst_path, node_factory):
        """Create or update hint from a MOVE event.

        Notes:
            In any case where we can't be 100% sure that the move hasn't be
            altered, the move hints are replaced by a couple
            (DeletedHint(), ModifiedHint())

        Args:
            tree (IndexTree): index of concerned node.
            scope (str): One of SCOPE_LOCAL or SCOPE_REMOTE.
            src_path (Text): source of the moved element.
            dst_path (Text): destination of the moved element.
            node_factory (Callable[[Text], BaseNode]): function used to create
                the destination node, if needed. It receives the node's name
                in argument and must return a single node.
        """
        with tree.lock:
            src_node = tree.get_node_by_path(src_path)
            dst_node = tree.get_or_create_node_by_path(dst_path, node_factory)
            dst_node.sync = False

            if src_node is None:  # Unusual case: source don't exists
                self._set_hint(dst_node, scope, ModifiedHint())
                return

            src_node.sync = False
            previous_src_hint = self._get_hint(src_node, scope)
            previous_dest_hint = self._get_hint(dst_node, scope)

            # "Break" the link between a couple of "moved" node, if we replace
            # one part of the move.
            if isinstance(previous_dest_hint, SourceMoveHint):
                state = self._get_state(dst_node, scope)
                self._set_hint(previous_dest_hint.dest_node, scope,
                               ModifiedHint(state))
            elif isinstance(previous_dest_hint, DestMoveHint):
                self._set_hint(previous_dest_hint.source_node, scope,
                               DeletedHint())

            if previous_src_hint is None:
                self._set_move_hints(scope, src_node, dst_node)
            elif isinstance(previous_src_hint, ModifiedHint):
                self._set_delete_hint(src_node, scope)
                self._set_hint(dst_node, scope, previous_src_hint)
            elif isinstance(previous_src_hint, DeletedHint):
                self._set_hint(dst_node, scope, ModifiedHint())
            elif isinstance(previous_src_hint, SourceMoveHint):
                _logger.warning('Two move event from the same source. This '
                                'should not happens. Path is "%s"', src_path)

                self._set_hint(previous_src_hint.dest_node, scope,
                               ModifiedHint())
                self._set_delete_hint(src_node, scope)
                self._set_hint(dst_node, scope, ModifiedHint())
            elif isinstance(previous_src_hint, DestMoveHint):
                # There are 2 subsequent moves. They're reduced in one move.
                # A --> B --> C become A --> C (and B is deleted)
                if previous_src_hint.source_node is dst_node:
                    # Special case: A --> B --> A
                    self._set_hint(dst_node, scope, None)
                else:
                    self._set_move_hints(scope, previous_src_hint.source_node,
                                         dst_node)
                self._set_delete_hint(src_node, scope)
