# -*- coding: utf-8 -*-


class BaseNode(object):
    """Node member of IndexTree, representing an object of a container.

    It represents an object (file or folder) stored in a container. It contains
    flags to see if the object is sync between local and server, and if all its
    descendants are sync.

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

    def add_child(self, node):
        """Add a child to this node.

        Args:
            node (BaseNode): new child.
        """
        node.parent = self
        self.children[node.name] = node
        if node._dirty:
            # propagate dirty flag
            node = self
            while node and not node._dirty:
                node._dirty = True
                node = node.parent

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
            # Clean all ancestors when theirs children are not dirty.
            node = self
            while node and node._sync:
                if any(child.dirty for child in node.children.values()):
                    break  # this node has at least one dirty child.
                node._dirty = False
                node = node.parent
        else:
            # Set all ancestors as dirty.
            node = self
            while node and not node._dirty:
                node._dirty = True
                node = node.parent
