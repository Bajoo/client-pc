# -*- coding: utf-8 -*-

from contextlib import contextmanager
import logging
import os.path
import threading
from ..common.strings import ensure_unicode
from .file_node import FileNode
from .folder_node import FolderNode

_logger = logging.getLogger(__name__)


class IndexTree(object):
    """Index all files in a container and manages metadata needed for sync.

    It contains either remote (server) information and local (filesystem) known
    information, and keep metadata about difference between local and remote.

    The structure is a tree, each node representing either a file or a folder.
    Nodes are named, each child is accessible by its filename.


    The main method is `browse_dirty_nodes()`, a generator which returns all
    nodes marked non-sync, until there is no more.

    All access to nodes must be protected by using the `self.lock`, including
    the read access to properties like hints.
    """

    # Special value, yielded by browse_all_non_sync_nodes()
    WAIT_FOR_TASK = object()

    def __init__(self):
        self.lock = threading.Lock()
        self._root = None

    def browse_all_non_sync_nodes(self):
        """Browse through the tree and yields all the non-sync nodes.

        Yield one by one, all nodes that are marked as "non-sync", until there
        is none. When the generator stops, the whole tree is in sync.

        The method must be used to "clean" the tree, meaning syncing all files
        corresponding to the yielded nodes. To do that, the generator releases
        the internal lock each time it yields, allowing the tree to be
        modified by external tasks.

        A node modified between two calls of the generator can provoke the
        generator yielding many times the same node. If a node has been cleaned
        and is marked dirty again, it will be yielded again in.

        When a node has a task assigned to it, it is temporary ignored. When
        all remaining non-sync nodes have a task assigned, the generator is
        "blocked": it can't returns node, but is not over yet. In this case, it
        yields a special value `WAIT_FOR_TASK`.
        The caller should try latter, when at least one task has been
        accomplished.

        Notes:
            The purpose of this method is to allow the caller to clean nodes
            through the use of tasks. If a node remains non-sync and without
            assigned task, it will be yielded again in another iteration,
            possibly the next one. The generator could yield indefinitely the
            same node.

            The yielded node has `task` attribute assigned to True. It means
            the node is "reserved" and should be assigned a task. If the caller
            don't assign it a task, it should set `node.task` to None.

        Return:
            Iterator[Union[IndexNode,IndexTree.WAIT_FOR_TASK]]: generator that
                will loop over all non-sync nodes.
        """
        last_iteration_was_empty = False
        with self.lock:
            while self._root and self._root.dirty:
                if last_iteration_was_empty:
                    # All non-sync nodes are blocked by tasks
                    with self._reverse_lock_context():
                        yield self.WAIT_FOR_TASK

                last_iteration_was_empty = True
                for node in self._browse_non_sync_nodes(self._root):
                    last_iteration_was_empty = False

                    node.task = True  # Set node "reserved" for a future task.
                    with self._reverse_lock_context():
                        yield node

    def _browse_non_sync_nodes(self, current_node):
        if not current_node.sync and current_node.task is None:
            yield current_node

        for node in (node for node in list(current_node.children.values())
                     if node.dirty and not node.removed and not node.error):
            # Note: The tree might change during a `yield`. `self._is_in_tree`
            # check that current_node is still part of the tree.
            for n in self._browse_non_sync_nodes(node):
                yield n

    @contextmanager
    def _reverse_lock_context(self):
        """Do the reverse of `with self.lock:`"""
        try:
            self.lock.release()
            yield
        finally:
            self.lock.acquire()

    def get_node_by_path(self, node_path):
        """Search and return a node from its file path.

        Notes:
            The lock must be acquired by the caller, to avoid race condition.
        Args:
            node_path (Text): path of the node, relative to the root folder.
        Returns:
            Optional[BaseNode]: if exists, the node referenced by this path.
        """
        node_path = ensure_unicode(node_path)
        node_names = os.path.normpath(node_path).split(os.path.sep)

        if node_names == ['.']:
            return self._root

        node = self._root
        for name in node_names:
            if node is None:
                return None
            node = node.children.get(name)
        return node

    def get_or_create_node_by_path(self, node_path, node_factory):
        """Search and return a node from its file path. Create it if needed.

        If the node don't exists, it will be created using a constructor
        provided by the caller. All missing nodes between the selected node and
        the root will be created as instances of FolderNode.

        Args:
            node_path (Text): path of the node, relative to the root folder.
            node_factory (Callable[[Text], BaseNode]): constructor of the leaf
                node.
        Return:
            BaseNode: node referenced by the path.
        """
        node_path = ensure_unicode(node_path)
        node_names = os.path.normpath(node_path).split(os.path.sep)

        if not self._root:
            self._root = FolderNode(u'.')

        if node_names == ['.']:
            return self._root

        node = self._root
        for idx, name in enumerate(node_names):
            parent = node
            node = parent.children.get(name)
            if node is None:
                if idx + 1 == len(node_names):
                    # leaf
                    node = node_factory(name)
                else:
                    node = FolderNode(name)
                parent.add_child(node)
        return node

    def set_tree_not_sync(self):
        """Set all tree nodes as not sync."""
        with self.lock:
            if self._root:
                self._root.set_all_hierarchy_not_sync()

    def load(self, data):
        """Load the tree from JSON data.

        There is two format used to store data. The "legacy" format (version
        prior to 0.4.0) and the actual one. If the legacy format is detected,
        `load()` will call `_legacy_load()`.

        The `data` dict contains two members:
        - 'version' contains the version format, and should be "2"
        - 'root': root node representing the top-level folder. If there is no
            information, "root" can be None.

        Each node has the following attributes:
        - "type": one of "FILE" or "FOLDER".
        - "children" (Optional[Dict]): list of children, under the form
        {u'name': node_def}.
        - "state" (Optional[Dict]): None, or dict representing the content of
            the node. Each Node subclass has its own values.
            FileNode have always two attributes `local_hash` and `remote_hash`.

        If an attribute is not present, it's considered equal as a None value.

        Examples:
            >>> data={
            ...     'version': 2,
            ...     'root': {
            ...         'type': 'FOLDER',
            ...         'state': None,
            ...         'children': {
            ...             'file.txt': {
            ...                 'type': 'FILE',
            ...                 'state': {
            ...                     'local_hash':
            ...                         '3f4855158eb3266a74cf3a5d78b361cc',
            ...                     'remote_hash':
            ...                         'd32239bcb673463ab874e80d47fae504'
            ...                 }
            ...             }
            ...         }
            ...     }
            ... }
            >>> tree = indexTree()
            >>> tree.load(data)

        Args:
            data (Dict): index tree data, crated by an `export_data()` call.
        """
        # Legacy format don't have a 'version' attribute, but it could have a
        # "version" file.
        try:
            format_version = int(data.get('version', 1))
        except TypeError:
            format_version = 1

        if format_version is 1:
            self._legacy_load(data)
            return

        # TODO: assert version is 2 ?

        root_def = data.get('root')
        if root_def:
            with self.lock:
                self._root = self._load_node(u'.', root_def)

    def _load_node(self, name, node_def):
        """Create a node instance from a node definition.

        Args:
            name (Text): name of the node.
            node_def (Dict): node definition. See `load(data)`.
        Returns:
            baseNode: Node created from definition.
        """

        if node_def.get('type') == "FOLDER":
            node = FolderNode(name)
        else:
            node = FileNode(name)

        node.set_state(node_def.get('state'))
        for (name, node_def) in node_def.get('children', {}).items():
            node.add_child(self._load_node(name, node_def))
        return node

    def _legacy_load(self, data):
        """Load index tree from legacy JSON file format.

        data is a flatten Dict. Each entry represent a file.
        There is no representation of folder. The presence of folder is
        determined from the presence of separator '/' in file paths.

        Examples:

            >>> data = {
            ...     u'file.txt': ('3f4855158eb3266a74cf3a5d78b361cc',
            ...                   'd32239bcb673463ab874e80d47fae504')
            ...     u'folder/file.txt': ('fcd56b5ada439b96cd1f3809df533f00',
            ...                          None)
            ... }
            >>> tree = IndexTree()
            >>> tree.load(data)

        Args:
            data (Dict[Text, Tuple[Optional[str], Optional[str]]]): dictionary
                of pair to insert into the index. The key is the file path and
                the value is a tuple of two hashes, the first one is the local
                hash, and the second is the remote hash.
        """
        with self.lock:
            self._root = None
            for path, (local_hash, remote_hash,) in data.items():
                node = self.get_or_create_node_by_path(path, FileNode)
                node.set_state({'local_hash': local_hash,
                                'remote_hash': remote_hash})

    def export_data(self):
        """Export all persistent data of the tree.

        Exported can be used to reload an index tree later (by calling the
        `load()` method).

        Returns:
            Dict: index data, under the form of Dict and List directly
                convertible to JSON format.
        """
        with self.lock:
            root = None
            if self._root:
                root = self._export_node(self._root)

            return {
                'version': 2,
                'root': root
            }

    def _export_node(self, node):
        """Export node in a serialized format convertible to JSON.

        Args:
            node (BaseNode): node to export.
        Returns:
            Dict: serialized node
        """
        if isinstance(node, FileNode):
            node_type = "FILE"
        else:
            node_type = "FOLDER"

        result = {
            'type': node_type
        }
        if node.state is not None:
            result['state'] = node.state
        if node.children:
            result['children'] = {name: self._export_node(child)
                                  for name, child in node.children.items()}
        return result

    def get_remote_hashes(self):
        """Get the flatten list of remote hashes of all file nodes.

        Note:
            Nodes that are not instance of FileNode are ignored.

        Returns:
            Dict[Text, str]: dict of all files, with file path as key and
                remote hash as value.
        """

        with self.lock:
            if not self._root:
                return {}
            return self._get_remote_hashes(self._root, {})

    def _get_remote_hashes(self, node, acc):
        if isinstance(node, FileNode) and node.state:
            if 'remote_hash' in node.state:
                acc[node.get_full_path()] = node.state['remote_hash']
        for child in node.children.values():
            self._get_remote_hashes(child, acc)
        return acc

    def is_dirty(self):
        """Determine if the tree is dirty or sync.

        An empty tree is always sync.

        Returns:
            bool: True if the tree is dirty; otherwise False.
        """
        with self.lock:
            return bool(self._root and self._root.dirty)
