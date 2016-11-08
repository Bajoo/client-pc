# -*- coding: utf-8 -*-


class BaseNode(object):
    """Node member of IndexTree, representing an object of a container.

    It represents an object (file or folder) stored in a container. It contains
    flags to see if the object is sync between local and server, and if all its
    descendants are sync.

    The two attributes `local_state` and `remote_state` are representations of
    the content's node. Theirs type are dependents of the Node type, and is
    defined in subclasses. Both local and remote states are of the same type.
    A None value means the target don't exist.
    Obviously, the state attributes are only the last version known to Bajoo.

    The two attributes `local_hint` and `remote_hint` are values set when an
    event is detected, and the node's corresponding value as changed. It's a
    "hint" that can be used for syncing the node.

    Attributes:
        name (Text): filename, used to represent the node.
        parent (Optional[BaseNode]): parent node. If None, this node is a root
            node.
        children (Dict[Text, Node]): list of child nodes, referenced by theirs
            names.
        sync (bool): Flag set to True when the node's inner content is sync.
            A file node is sync if the local and remote version are the same,
            and all metadata stored in the node are correct.
            A folder node is sync if all its data are matching the tree state
            (each file in the folder has a node, no unknown node, ...).
        dirty (bool, read-only): Flag set to True when the node or one of its
            descendants is not sync. Its value is updated over the hierarchy
            when `sync` changes.
        task (Any): if not None, there is an ongoing operation to sync this
            node. This task object means the node is "in use" and another task
            should not work on the same node.
        local_state (Any): last known state of the node content, local-side
        remote_state (Any):last known state of the node content, remote-side
        local_hint (Optional[Hint]): if set, hint representing the presumed
            local modifications of the content pointed by this node.
        remote_hint (Optional[Hint]): if set, hint representing the presumed
            remote modifications of the content pointed by this node.
    Notes:
        `sync` refers to the node only; `dirty` refers the hierarchy. A
        non-sync node is always dirty.
    """

    def __init__(self, name):
        """Node constructor

        Args:
            name (Text): file name of the node.
        """
        self.name = name
        self.parent = None
        self.children = {}
        self._sync = False
        self._dirty = True

        self.local_state = None
        self.remote_state = None

        self.task = None
        self.local_hint = None
        self.remote_hint = None

    def add_child(self, node):
        """Add a child to this node.

        Args:
            node (BaseNode): new child.
        """
        node.parent = self
        self.children[node.name] = node
        if node.dirty:
            self._propagate_dirty_flag()

    def rm_child(self, node):
        """Remove a child from this node."""
        del self.children[node.name]
        if node.dirty:
            # will recalculate the dirty flag.
            self._clean_dirty_flags()
        node.parent = None

    @property
    def dirty(self):
        """Read-only dirty flag"""
        return self._dirty

    @property
    def sync(self):
        """sync flag Getter"""
        return self._sync

    @sync.setter
    def sync(self, flag):
        """Set the sync flag, and update the hierarchy consequently.

        Raising the flag 'sync' will mark the node and all its ancestors as not
        dirty, as long as all node's children are also clean.
        On the contrary, removing the `sync` flag will raise the `dirty` flag
        on this node and all its ancestors.

        Args:
            flag (bool): new value for the `sync` flag.
        """
        self._sync = flag  # La sync ne change que pour nous !

        if self._sync:
            self._clean_dirty_flags()
        else:
            self._propagate_dirty_flag()

    def _propagate_dirty_flag(self):
        """Set this node and all ancestors as dirty."""
        node = self
        while node and not node._dirty:
            node._dirty = True
            node = node.parent

    def _clean_dirty_flags(self):
        """Clean dirty flag for this node and all its ancestors."""
        node = self
        while node and node._sync:
            if any(child.dirty for child in node.children.values()):
                break  # this node has at least one dirty child.
            node._dirty = False
            node = node.parent

    def remove_itself(self):
        """Remove itself from the tree."""
        if self.parent:
            self.parent.rm_child(self)

    def exists(self):
        """Check if the node physically existed the last time it was sync.

        Note:
            If the target has been created after the last sync, it will still
            returns True. It only considers the synced data (and ignore the
            hints).

        Returns:
            bool: True if it exists; otherwise False
        """
        return self.local_state is not None or self.remote_state is not None

    def set_all_hierarchy_not_sync(self):
        """Set the sync flag to false for this node and all its children.

        Note: this method does not update the parent node! It should be used
        only on root nodes.
        """
        self._sync = False
        for child in self.children.values():
            child.set_all_hierarchy_not_sync()
