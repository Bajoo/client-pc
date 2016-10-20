# -*- coding: utf-8 -*-

from contextlib import contextmanager
import logging
import os.path
import threading
from ..common.strings import ensure_unicode
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
                    with self._reverse_lock_context():
                        yield node

    def _browse_non_sync_nodes(self, current_node):
        if not current_node.sync:
            if current_node.task is None:  # nodes with task are ignored.
                yield current_node
        for node in filter(lambda n: n.dirty, current_node.children.values()):
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
