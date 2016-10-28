# -*- coding: utf-8 -*-

from ..index.new_index_tree import IndexTree


class SyncScheduler(object):
    """Browse dirty indexes and find the node that should be cleaned first.

    It contains the list of IndexTree to browse. The scheduler handles the
    different states of the trees (some are clean, some are waiting for task to
    finish, ...), and returns the node (with `get_node()`) in the best order
    possible.

    When possible, the scheduler try to grep the nodes per tree.
    """

    def __init__(self):
        self._index_trees = []

        # index of, the next tree to browse in self._index_trees
        self._index_next_tree = 0

        self._generators = []

    def add_index_tree(self, tree):
        """Add a new tree to browse.

        Args:
            tree (IndexTree): new tree to browse.
        """
        self._index_trees.append(tree)

    def remove_index_tree(self, tree):
        """Remove an index tree from the list

        If it's not in the list, do nothing.

        Args:
            tree (IndexTree): the tree to remove.
        """

        try:
            self._index_trees.remove(tree)
        except ValueError:
            return

        if self._index_next_tree >= len(self._index_trees):
            self._index_next_tree = 0

        for idx, data_tree in enumerate(self._generators):
            if data_tree['tree'] is tree:
                data_tree['gen'].close()
                del self._generators[idx]
                return

    def get_node(self):
        """Find the next node that should be sync.

        Returns:
            Optional[Node]: the next node to sync, if there is one available.
        """

        for data_tree in self._generators[:]:
            try:
                node = next(data_tree['gen'])
            except StopIteration:
                self._generators.remove(data_tree)
            else:
                if node is not IndexTree.WAIT_FOR_TASK:
                    return node

        if not self._index_trees:
            return None

        # new generator needed;
        start_index = self._index_next_tree
        while True:
            tree = self._index_trees[self._index_next_tree]
            gen = tree.browse_all_non_sync_nodes()

            self._index_next_tree += 1
            if self._index_next_tree >= len(self._index_trees):
                self._index_next_tree = 0

            try:
                node = next(gen)
            except StopIteration:
                pass  # clean tree
            else:
                self._generators.append({'tree': tree, 'gen': gen})
                if node is not IndexTree.WAIT_FOR_TASK:
                    return node

            if self._index_next_tree == start_index:
                # We've tested all trees.
                return None
