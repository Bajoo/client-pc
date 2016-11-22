# -*- coding: utf-8 -*-


class BaseNode(object):
    """Node member of IndexTree, representing an object of a container.

    It represents an object (file or folder) stored in a container. It contains
    flags to see if the object is sync between local and server, and if all its
    descendants are sync.

    The `state` attribute is a representation of the node content. It's a
    Dict containing all metadata related to the node. Its content depend of
    the Node type, and is defined in each Node subclass.
    Obviously, the state attribute only contains the last version known to
    Bajoo (ie: the last "sync" version).
    If the state is None, it means the node doesn't exists as visible entity in
    Bajoo: it can be a new file, not yet sync. Such node will be processed,
    either by being assigned a state or by being deleted.

    a Node with a None state and children are a special case: they don't have
    an existence known by Bajoo, but must exists to contains theirs children.
    It the case of regular folders.

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
        state (Optional[Dict]): last known state of the node content. Its
            content depends of the Node subclass.
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

        self.state = None

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
            If the node has been created after the last sync, it will still
            returns False. It only considers the synced data (and ignore the
            hints).
            Root node always exists.

        Returns:
            bool: True if it exists; otherwise False
        """
        return (self.state is not None or self.children or
                self.parent is None)

    def set_all_hierarchy_not_sync(self):
        """Set the sync flag to false for this node and all its children.

        Note: this method does not update the parent node! It should be used
        only on root nodes.
        """
        self._sync = False
        for child in self.children.values():
            child.set_all_hierarchy_not_sync()

    def get_full_path(self):
        """Return the path of the node, relative to the root node.

        The root node always returns '.', and nodes that are direct child of
        the root node returns theirs names.

        Returns:
            Text: full path, composed of each node's names separated by a '/'.
        """
        if self.parent is None:
            return u'.'

        path_part = []
        node = self
        while node:
            path_part.append(node.name)
            node = node.parent

        path_part.reverse()

        return u'/'.join(path_part[1:])

    def set_state(self, state):
        """Set the state of the node.

        This method is destined to be overridden to add specific check for
        subclass.

        Args:
            state (Optional[Dict]): new state
        """
        self.state = state

    def release(self):
        """Release the node reserved by a task.

        If no other events (hints) has been set meanwhile, it also set the
        node as sync.
        if the node's state is None, and the node has not child, it's removed
        from the tree.
        """
        self.task = None
        if not self.local_hint and not self.remote_hint:
            if not self.exists():
                parent_node = self.parent
                self.remove_itself()

                # if parent is also empty, trigger a chain deletion.
                if parent_node and not parent_node.exists():
                    parent_node.sync = False
            else:
                self.sync = True
