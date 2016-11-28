# -*- coding: utf-8 -*-

import logging
from threading import RLock

from ..promise import Deferred, Promise
from ..filesync.added_local_files_task import AddedLocalFilesTask
from ..filesync.added_remote_files_task import AddedRemoteFilesTask
from ..filesync.exception import RedundantTaskInterruption
from ..filesync.moved_local_files_task import MovedLocalFilesTask
from ..filesync.removed_local_files_task import RemovedLocalFilesTask
from ..filesync.removed_remote_files_task import RemovedRemoteFilesTask
from ..filesync.sync_task import SyncTask
from ..filesync.task_consumer import add_task
from .index_node import DirectoryNode
from .index_node import FileNode

_logger = logging.getLogger(__name__)


def trigger_local_create_task(filename, previous_task):
    """ This function trigger an AddedLocalFilesTask

    Args:
        filename<String>: the target path of the task
        previous_task<_Task>: a previous task working in the same local
            container

    Return
        The new created AddedLocalFilesTask
    """
    create_task = AddedLocalFilesTask(previous_task.container,
                                      (filename,),
                                      previous_task.local_container,
                                      create_mode=True)
    add_task(create_task, priority=True)
    return create_task


def trigger_local_delete_task(filename, previous_task):
    """ This function trigger a RemovedLocalFilesTask

    Args:
        filename<String>: the target path of the task
        previous_task<_Task>: a previous task working in the same local
            container

    Return
        The new created RemovedLocalFilesTask
    """
    delete_task = RemovedLocalFilesTask(previous_task.container,
                                        (filename,),
                                        previous_task.local_container)
    add_task(delete_task, priority=True)
    return delete_task


def trigger_local_moved_task(src, dest, previous_task):
    """ This function trigger a MovedLocalFilesTask

    Args:
        src<String>: the target source path of the task
        dest<String>: the target destination path of the task
        previous_task<_Task>: a previous task working in the same local
            container

    Return
        The new created MovedLocalFilesTask
    """
    moved_task = MovedLocalFilesTask(previous_task.container,
                                     (src, dest,),
                                     previous_task.local_container)
    add_task(moved_task, priority=True)
    return moved_task


class IndexTree(object):

    def __init__(self, index_saver, init_dict=None):
        """ Constructor of the index tree

        Args:
            index_saver<IndexSaver>: an instance of the object to trigger if
                a change is detected and must be saved in the index

            init_dict<dict>: dictionary of pair to insert into the index.
                The key is the file path and the value is a tuple of two
                hashes, the first one is the local hash, and the second is
                the remote hash.
        """

        self.root = DirectoryNode(path_part=u"")
        self.locked_count = 0
        self.lock = RLock()
        self.promise_waiting_for_task = {}
        self.index_saver = index_saver

        if init_dict is not None:
            self.load(init_dict)

    def load(self, init_dict):
        """ Load a dictionary into the index

        ATTENTION: it does not remove the existing value

        Args:
            init_dict<dict>: dictionary of pair to insert into the index.
                The key is the file path and the value is a tuple of two
                hashes, the first one is the local hash, and the second is
                the remote hash.

        """
        for path, (local_hash, remote_md5,) in init_dict.items():
            node = self.root.get_or_insert_node(path,
                                                index_saver=self.index_saver)
            node.set_hash(local_hash, remote_md5, trigger=False)

    def acquire(self, target_list, task, prior_acquire=False):
        """ This method tries to acquire the target paths in the index

        Args:
            target_list<List<string>>: a list of path to lock

            task<object>: the task object to use on this acquire

            prior_acquire<bool>: if set to True and if the target is not
                free, the task will be the first to get the lock
                on the node as soon as it will be available again.

        Returns:
            Promise (List<FileNode>): return a list of node in the same order
                as the input target_list.  If the task has been cancelled
                by the merge algorithm, the Promise will be rejected with
                a RedundantTaskInterruption.
        """
        # the task was created during the merge algorithm and already has a
        # assigned promise waiting for it.
        if task in self.promise_waiting_for_task:
            return self.promise_waiting_for_task.pop(task)

        if len(target_list) == 0:
            return Promise.resolve({})

        # only moved task can ask two target
        if ((len(target_list) == 2 and
             not isinstance(task, MovedLocalFilesTask)) or
                len(target_list) > 2):
            raise Exception("try to acquire more path than needed for a task")

        ordered_target_list = sorted(target_list)

        # TODO
        #   can't allow a sync task to have more than 1 target
        #   because it will break the current stealing system

        with self.lock:
            node_dict = {}
            for target_path in ordered_target_list:
                node = self.root.get_or_insert_node(
                    target_path,
                    only_directory=isinstance(task, SyncTask),
                    index_saver=self.index_saver)

                # we already hold the lock on this node, nothing to do.
                if node.is_locked() and node.executing_task is task:
                    node_dict[target_path] = node
                    continue

                # a sync already exist on the current node or on an ancestor
                if isinstance(node, DirectoryNode):
                    parent_sync = node
                    while parent_sync is not None:
                        if parent_sync.waiting_task is not None:
                            break

                        parent_sync = parent_sync.parent

                    if parent_sync is not None:
                        self._inner_release(ordered_target_list, task)

                        if prior_acquire:
                            parent_sync.set_prior()

                        node.self_remove_if_possible()
                        return Promise.reject(RedundantTaskInterruption())

                # a task is already waiting on the current node, try to merge
                if node.waiting_task is not None:
                    if self._use_the_new_task(node, task):
                        # cancel the previous task
                        node.cancel_waiting_task(
                            remove_from_waiting_list=False)

                        # replace with the new one
                        return self._generate_waiting_promise(
                            node,
                            ordered_target_list,
                            task,
                            prior_acquire)
                    else:
                        if prior_acquire:
                            node.set_prior()

                        self._inner_release(ordered_target_list, task)
                        return Promise.reject(RedundantTaskInterruption())

                # node is locked but without task on it
                if node.is_locked():
                    promise = self._generate_waiting_promise(
                        node,
                        ordered_target_list,
                        task,
                        prior_acquire)

                    node.lock_owner.add_waiting_node(node, prior_acquire)
                    return promise

                # search for a locked parent
                locked_parent = node.parent
                while locked_parent is not None:
                    if locked_parent.is_locked():
                        break
                    locked_parent = locked_parent.parent

                if locked_parent is not None:
                    # if a parent is locked, need to lock every node
                    # between this parent and the target node
                    # this case occurs when a new path is inserted in
                    # a locked part of the tree
                    current_node = node
                    while current_node is not locked_parent:
                        current_node.lock(locked_parent.lock_owner)
                        current_node.parent.increment_children_locked_count()
                        current_node = current_node.parent

                    promise = self._generate_waiting_promise(
                        node,
                        ordered_target_list,
                        task,
                        prior_acquire)

                    locked_parent.add_waiting_node(node, prior_acquire)
                    return promise

                # if directory node, need to lock every children
                if isinstance(node, DirectoryNode):
                    self._steal_sync_task_on_children(node)

                    blocking_node = self._lock_children(node)
                    if blocking_node is not None:
                        promise = self._generate_waiting_promise(
                            node,
                            ordered_target_list,
                            task,
                            prior_acquire)

                        blocking_node.add_waiting_node(node, prior_acquire)
                        return promise

                # lock the node
                node.lock(executing_task=task)
                self.locked_count += 1
                node_dict[target_path] = node

            result_list = []
            for target_path in target_list:
                result_list.append(node_dict[target_path])

            return Promise.resolve(result_list)

    def release(self, target_list, task):
        """ Release every path locked by the task

        Args:
            target_list<List<string>>: a list of path to unlock
            task<object>: the task used to lock the list of path
        """
        with self.lock:
            self._inner_release(target_list, task)

    def is_locked(self):
        """ Check if a task has locked a part of the tree

        Returns:
            boolean: True if at least one task is locked in the tree,
                     False otherwise
        """

        return self.locked_count != 0

    def export_data(self):
        """ Generate a dictionary with the correct format to be stored in
            a json file.

        Returns:
            Dict: The key is the file path and the value is a tuple of two
                hashes, the first one is the local hash, and the second is
                the remote hash.
        """
        output = {}
        with self.lock:
            for child in self.root.traverse_only_file_node():
                output[child.get_complete_path()] = (child.local_md5,
                                                     child.remote_md5)

        return output

    def generate_dict_with_remote_hash_only(self):
        """ Generate a dict with file path as key and remote hash as value.
            It will be used to check if the remote hash has been modified
            on the server.

        Returns:
            Dict: The key is the file path and the value is the remote hash.
        """
        output = {}
        with self.lock:
            for child in self.root.traverse_only_file_node():
                output[child.get_complete_path()] = child.remote_md5

        return output

    def get_node(self, path):
        """ This method is used to extract a specific node from the tree

        Arg:
            path<string>: the path of the target node

        Return:
            A node if the path exists in the tree, None otherwise
        """
        with self.lock:
            return self.root.get_or_insert_node(path, create=False)

    def _inner_release(self, target_list, task):
        """ Release every path locked by the task

        ATTENTION: self.lock has to be acquired before to execute this method

        Args:
            target_list<List<string>>: a list of path to unlock
            task<object>: the task used to lock the list of path

        """

        for target_path in target_list:
            node = self.root.get_or_insert_node(target_path, create=False)

            # TODO improvment, allow to free a partialy locked directory tree

            if (node is None or
                    not node.is_locked() or
                    not node.is_lock_owner() or
                    node.executing_task is not task):
                continue

            node.unlock()
            self.locked_count -= 1
            node.self_remove_if_possible()

            self.lock.release()
            node.trigger_waiting_nodes()
            self.lock.acquire()

    def _generate_waiting_promise(self,
                                  node,
                                  target_list,
                                  task,
                                  prior_acquire=False):
        """ This method generates a Promise and assigns a callback to
            the waiting node.

        Args:
            node: the node where to assign the callback
            target_list<list<string>>:  if the callback is called, a new call
                to the method acquire will occur, the method need to know
                the list of target
            task<_Task>: the waiting task
            prior_acquire<bool>: same as target_list

        Return:
            the generated Promise
        """
        df = Deferred()

        def callback(cancel=False, release_aquired_lock=True):
            if cancel:
                if release_aquired_lock:
                    self.release(target_list, task)
                df.reject(RedundantTaskInterruption())
            else:
                p = self.acquire(target_list, task, prior_acquire)
                p.then(df.resolve, df.reject)

        node.set_waiting_task(task, callback)

        return df.promise

    def _steal_sync_task_on_children(self, node):
        """ This method steals every child node locked by every
            waiting sync_task.
            The sub sync_task will also be canceled

        Args:
            node: the node where will be set the new sync_task.

        """

        # iterate only on sub directory node
        for child_dir_node in node.traverse_only_directory_node():
            # no sync_task on this node
            if child_dir_node.waiting_task is None:
                continue

            # cancel sync_task on this node
            child_dir_node.cancel_waiting_task()

            # the node is running, can't steal its lock
            if child_dir_node.is_lock_owner():
                continue

            # collect waiting nodes
            node.waiting_nodes.extend(child_dir_node.waiting_nodes)
            del node.waiting_nodes[:]

            # collect locked nodes
            for sub_child_dir_node in child_dir_node.traverse():
                if sub_child_dir_node.lock_owner == child_dir_node:
                    sub_child_dir_node.lock_owner = node

    def _lock_children(self, starting_node):
        """ This method tries to lock every child nodes, internal or
            external node.

            The starting_node won't be locked by this method.

        Arg:
            starting_node: the method will start to search nodes to lock
                in the children of this node.

        Return:
            If the algorithm meets a node locked by another process, it stops
            the traversal an returns this node.  If every nodes have been
            locked, the algorithm returns None.
        """

        def explore(node):
            return node.has_children_unlocked()

        def collect(node):
            return isinstance(node, FileNode)

        for file_node in starting_node.traverse(explore, collect):
            if file_node.is_locked():
                if file_node.lock_owner is starting_node:
                    continue
                else:
                    return file_node

            file_node.lock(owner=starting_node)

            parent_node = file_node
            while parent_node.parent != starting_node:
                parent_node = parent_node.parent
                parent_node.increment_children_locked_count()

                if parent_node.has_children_unlocked():
                    break

                parent_node.lock(owner=starting_node)

            # TODO what about empty sub directory ?
            #   no supposed to exist in the tree

        return None

    def _use_the_new_task(self, node, new_task):
        """ This method is the brain of the merge task algorithm.
            It will decide if a new task on a path must be discarded or
            be kept.

            It is not only a decision algorithm, it will sometime make a part
            of the merging process, depending the case.

            NOTE: the merge part for the sync_task occur in the aquire process

        Args:
            node: the node where a task is already waiting
            new_task<_Task>: the new task that would like to lock this node

        Return:
            False if the new_task should be discarded
            True if the old_task is replaced by the new_task
        """

        task = node.waiting_task

        if isinstance(task, AddedLocalFilesTask):
            if isinstance(new_task, MovedLocalFilesTask):
                node.invalidate_local()
                return True

            if isinstance(new_task, RemovedLocalFilesTask):
                return True

            if isinstance(new_task, AddedLocalFilesTask):
                if new_task.create_mode:
                    task.create_mode = True

                return False

            elif (isinstance(new_task, AddedRemoteFilesTask) or
                    isinstance(new_task, RemovedRemoteFilesTask)):
                node.invalidate_remote()
                return False

        elif isinstance(task, RemovedLocalFilesTask):
            if isinstance(new_task, MovedLocalFilesTask):
                node.invalidate_local()
                return True

            if isinstance(new_task, AddedLocalFilesTask):
                return True

            if isinstance(new_task, AddedRemoteFilesTask):
                node.invalidate_local()
                return True

            if isinstance(new_task, RemovedRemoteFilesTask):
                node.invalidate_remote()
                return False

        elif isinstance(task, AddedRemoteFilesTask):
            if isinstance(new_task, MovedLocalFilesTask):
                node.invalidate_remote()
                return True

            if isinstance(new_task, RemovedRemoteFilesTask):
                return True

            if (isinstance(new_task, AddedLocalFilesTask) or
                    isinstance(new_task, RemovedLocalFilesTask)):
                node.invalidate_local()
                return False

        elif isinstance(task, RemovedRemoteFilesTask):
            if isinstance(new_task, MovedLocalFilesTask):
                node.invalidate_remote()
                return True

            if isinstance(new_task, AddedRemoteFilesTask):
                return True

            if isinstance(new_task, AddedLocalFilesTask):
                node.invalidate_remote()
                return True

            if isinstance(new_task, RemovedLocalFilesTask):
                node.invalidate_local()
                return False

        elif isinstance(task, MovedLocalFilesTask):
            if isinstance(new_task, MovedLocalFilesTask):
                node_path = node.get_complete_path()

                task_src = task.target_list[0]
                task_dest = task.target_list[1]

                new_task_src = new_task.target_list[0]
                new_task_dest = new_task.target_list[1]

                # copy of the same move, discard!
                if task_src == new_task_src and task_dest == new_task_dest:
                    return False

                if node_path == task_src:
                    if node_path == new_task_src:
                        # nothing is locked yet
                        # a moved_task.src is waiting on the node
                        # a new moved_task.src is trying to aquire the node

                        self._replace_task_with_create_task(node, task)
                        node.invalidate_remote()

                        trigger_local_create_task(task_dest, task)
                        dest_node = self.root.get_or_insert_node(task_dest,
                                                                 create=False)
                        if dest_node is not None:
                            # invalide the remote hash ensure a check of the
                            # server state in the local create task
                            dest_node.invalidate_remote()

                        trigger_local_create_task(new_task_dest, new_task)
                        dest_node = self.root.get_or_insert_node(
                            new_task_dest,
                            create=False)
                        if dest_node is not None:
                            # invalide the remote hash ensure a check of the
                            # server state in the local create task
                            dest_node.invalidate_remote()

                        return False
                    else:
                        # new_task_src is locked
                        # a moved_task.src is waiting on the node
                        # a new moved_task.dst is trying to aquire the node

                        create_task = trigger_local_create_task(task_dest,
                                                                task)
                        dest_node = self.root.get_or_insert_node(task_dest,
                                                                 create=False)

                        if dest_node is not None:
                            # invalide the remote hash ensure a check of the
                            # server state in the local create task
                            dest_node.invalidate_remote()
                            if dest_node.is_invalidate_local():
                                create_task.create_task = False

                        return True
                else:
                    if node_path == new_task_src:
                        # task_src is locked
                        # a moved_task.dst is waiting on the node
                        # a new moved_task.src is trying to aquire the node

                        # execute the cancel task outside the replace task
                        # to keep the lock on the aquired source node
                        node.cancel_waiting_task(
                            remove_from_waiting_list=False,
                            release_aquired_lock=False)

                        self._replace_task_with_delete_task(node,
                                                            task,
                                                            cancel_task=False)

                        moved_task = trigger_local_moved_task(task_src,
                                                              new_task_dest,
                                                              task)

                        src_node = self.root.get_or_insert_node(task_src,
                                                                create=False)
                        if (src_node is not None and
                                isinstance(src_node, FileNode)):
                            if src_node.executing_task is task:
                                src_node.executing_task = moved_task

                        return False
                    else:
                        # task_src is locked
                        # new_task_src is locked
                        # a moved_task.dst is waiting on the node
                        # a new moved_task.dst is trying to aquire the node

                        trigger_local_delete_task(task_src, task)
                        return True

            elif (isinstance(new_task, AddedRemoteFilesTask) or
                  isinstance(new_task, RemovedRemoteFilesTask)):
                node.invalidate_remote()
            elif (isinstance(new_task, AddedLocalFilesTask) or
                  isinstance(new_task, RemovedLocalFilesTask)):
                node.invalidate_local()
        else:
            _logger.error("Unkown task type %s, don't know if it must kept"
                          " or discarded." % type(task))

        return False

    def _replace_task(self,
                      node,
                      filename,
                      new_task,
                      cancel_task=True):
        """ This method replace a waiting task with another one.

        Args:
            node: the node where the new task has to be set
            filename<string>: the access path to the node, it will be used
                to generate the new callback
            new_task<_Task>: the new waiting task
            cancel_task<bool>: if set to true, the previous waiting task will
                be cancelled. If set to False, the previous task has to be
                cencelled outside of this method.
        """

        if cancel_task:
            node.cancel_waiting_task(remove_from_waiting_list=False)

        promise = self._generate_waiting_promise(node,
                                                 (filename,),
                                                 new_task)

        self.promise_waiting_for_task[new_task] = promise
        add_task(new_task, priority=True)

    def _replace_task_with_create_task(self,
                                       node,
                                       previous_task,
                                       cancel_task=True):
        """ This method replace a waiting task with an AddedLocalFilesTask.

        Args:
            node: the node where the new task has to be set
            previous_task<_Task>: a previous waiting task working in the same
                local container.
            cancel_task<bool>: if set to true, the previous waiting task will
                be cancelled. If set to False, the previous task has to be
                cencelled outside of this method.

        Return:
            the new AddedLocalFilesTask
        """

        filename = node.get_complete_path()
        create_task = AddedLocalFilesTask(previous_task.container,
                                          (filename,),
                                          previous_task.local_container,
                                          create_mode=True)
        self._replace_task(node, filename, create_task, cancel_task)
        return create_task

    def _replace_task_with_delete_task(self,
                                       node,
                                       previous_task,
                                       cancel_task=True):
        """ This method replace a waiting task with a RemovedLocalFilesTask.

        Args:
            node: the node where the new task has to be set
            previous_task<_Task>: a previous waiting task working in the same
                local container.
            cancel_task<bool>: if set to true, the previous waiting task will
                be cancelled. If set to False, the previous task has to be
                cencelled outside of this method.

        Return:
            the new RemovedLocalFilesTask
        """

        filename = node.get_complete_path()
        delete_task = RemovedLocalFilesTask(previous_task.container,
                                            (filename,),
                                            previous_task.local_container)

        self._replace_task(node, filename, delete_task, cancel_task)
        return delete_task
