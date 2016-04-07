# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod

from ..common.strings import to_str


def split_path(path):
    """This method is used to clean and split a path.  The result will only
       be the text tokens of the path.

    Args:
        path: a not cleaned unicode string that represent a path using the
            unix file separator

    Return:
        Tuple<String>: a tuple of string that compose the input path

    Input => Output example:
        u"" => ()
        u"." => ()
        u"/" => ()
        u"./" => ()
        u"part1/part2/part3" => ("part1", "part2", "part3",)
        u"/part1/part2/part3" => ("part1", "part2", "part3",)
        u"./part1/part2/part3" => ("part1", "part2", "part3",)
        u"part1/part2/part3/" => ("part1", "part2", "part3",)
        u"part1//part2///part3" => ("part1", "part2", "part3",)
    """

    if path is None or path == u".":
        return ()

    if path.startswith(u"./"):
        path = path[2:]
    elif path.startswith(u"/"):
        path = path[1:]

    if path.endswith(u"/"):
        path = path[:-1]

    if len(path) == 0:
        return ()

    final_result = []

    for token in path.split(u"/"):
        if len(token) == 0:
            continue

        final_result.append(token)

    return tuple(final_result)


def _accept_any(node=None):
    """ Dummy function to accept anything in traversal """
    return True


class AbstractNode(object):
    """ This abstract node represents the common part for the directory
        and file node.

    Attributes:
        parent<node>: the parent node, None if the current node is the root.
        lock_owner<node>: the node that has locked this node, None if
            not locked.
        executing_task<_Task>: the task in execution on this node.
        waiting_task<_Task>: the task waiting to be executed on this node.
            It could be waiting because this node, a child or a parent is
            locked by another node.
        waiting_task_callback<fun>: the callback associated to the waiting
            task. The execution of this callback will continue the task.
        waiting_for_node<node>: a node locked by another task and needed
            by the waiting task set on this node.  waiting_for_node can
            be the current node, a child or a parent.
        path_part<string>: the last part of the path needed to access this
            node.  The other parts needed to access this node are stored
            in the parents.
    """
    __metaclass__ = ABCMeta

    def __init__(self, path_part, parent=None):
        self.parent = parent
        self.lock_owner = None
        self.executing_task = None
        self.waiting_task = None
        self.waiting_task_callback = None
        self.waiting_for_node = None
        self.path_part = path_part

    def get_complete_path(self):
        """ This method generates the complete path to access this node from
            the root node.

        Return
            the complete string path of this node.
        """
        path_part = []

        node = self
        while node is not None:
            path_part.append(node.path_part)
            node = node.parent

        path_part.reverse()

        joined_path = u"/".join(path_part)

        if len(joined_path) == 0:
            return u"."

        return u".%s" % joined_path

    def __str__(self):
        return to_str(self.get_complete_path())

    def __repr__(self):
        return str(self)

    def is_removable(self):
        """ This method decide is it is usefull to keep the node in the tree

        Return:
            True if the node can be removed from the tree, False otherwise.
        """
        return (self.parent is not None and
                self.lock_owner is None and
                self.waiting_task is None)

    def self_remove_if_possible(self):
        """ This method remove nodes until it reach a usefull parent """

        current_node = self
        while current_node.is_removable():
            current_node.parent.remove_child(current_node)
            current_node = current_node.parent

    @abstractmethod
    def remove_child(self, node):
        """ remove a child from this node

        Arg:
            node<node>: the node to remove
        """
        pass

    def lock(self, owner=None, executing_task=None):
        """ this method lock the node and set the executing task

        Args:
            owner<node>: the owner lock node
            executing_task<_Task>: the executing task requiring this node
        """
        if owner is None:
            owner = self

        if self.lock_owner is None:
            self.lock_owner = owner

            if owner is self:
                self.executing_task = executing_task

    def unlock(self, owner=None):
        """ this method unlock the node and unset the executing task

        Arg:
            node<node>: the owner lock
        """
        if owner is None:
            owner = self

        if self.lock_owner == owner:
            self.lock_owner = None
            self.executing_task = None

    def trigger_waiting_task(self):
        """ this method trigger the waiting task if it exists """
        if self.waiting_task is not None:
            callback = self.waiting_task_callback
            self.waiting_task_callback = None
            self.waiting_task = None
            self.waiting_for_node = None
            callback()

    def is_locked(self):
        """ this method returns True is the node is locked, False otherwise
        """
        return self.lock_owner is not None

    def is_lock_owner(self):
        """ this method returns True is the node is the owner of its self
            lock.
         """
        return self.lock_owner is self

    @abstractmethod
    def add_waiting_node(self, node):
        """ add a waiting node

        Arg:
            node<node>: a node waiting for this node to be unlocked
        """
        pass

    @abstractmethod
    def remove_waiting_node(self, node=None):
        """ remove a waiting node

        Arg:
            node<node>: a node waiting for this node to be unlocked
        """
        pass

    @abstractmethod
    def set_prior(self, node=None):
        """ set a waiting node prior

        Arg:
            node<node>: set the node as the most prior in the other waiting
                nodes.
        """
        pass

    @abstractmethod
    def trigger_waiting_nodes(self):
        """ trigger waiting nodes """
        pass

    def cancel_waiting_task(self,
                            remove_from_waiting_list=True,
                            release_aquired_lock=True):
        """ This method cancel a waiting task by calling its callback function
            with the cancel flag set to True

        Args:
            remove_from_waiting_list<bool>: if set to True, the node will be
                removed from the waiting_list of the waited node.
            release_aquired_lock<bool>: this flag will be passed to the
                callback.  If set to True, every path acquired by the task
                will be released.
        """

        if self.waiting_task is None:
            return

        if remove_from_waiting_list:
            self.waiting_for_node.remove_waiting_node(self)
            self.waiting_for_node = None

        callback = self.waiting_task_callback
        self.waiting_task_callback = None
        self.waiting_task = None
        callback(cancel=True, release_aquired_lock=release_aquired_lock)

    def set_waiting_task(self, waiting_task, callback):
        """ set a waiting task and its callback on this node

        Args:
            waiting_task<_Task>: the task waiting for this node to be unlocked
            callback<fun>: a callback function to restart the aquire process
                linked to the waiting task.  This callback function has to
                manage two arguments:
                    cancel<bool>: if set to True, it indicate to the task to
                        stop its acquiring process.
                    release_aquired_lock<bool>: if set to True, it indicate
                        to the task to free every other locked nodes.
        """

        self.waiting_task = waiting_task
        self.waiting_task_callback = callback

    def traverse(self, explore=None, collect=_accept_any):
        """ traverse the tree from this node

        Args:
            explore<fun>: a one arg<node> function, it should return True
                if the node has to be explored for more children.
            collect<fun>: a one arg<node> function, it should return True
                if the node has to be collect by the generator.
        """
        if collect(self):
            yield self

    @abstractmethod
    def traverse_only_directory_node(self):
        """ traverse the tree and only returns directory nodes """
        pass

    @abstractmethod
    def traverse_only_file_node(self):
        """ only returns file nodes """
        pass


class DirectoryNode(AbstractNode):
    """ This class represents a directory node that stores child nodes.
        A child node can be a directory or a file node.
        A directory node without any child is not allowed in the tree.

    Attributes:
        children<dict<node>>: a dict of children.  The key is the last part
            of the path needed to reach the node.  The value is a node, it
            can be a directory or a file node.
        waiting_nodes<list<node>>: the list of node waiting for this node to
            be unlocked.
        locked_children<integer>: the count of locked children.  This
            attribute is used during the locking process.
    """

    def __init__(self, path_part, parent=None):
        AbstractNode.__init__(self, path_part, parent)

        self.children = {}
        self.waiting_nodes = []
        self.locked_children = 0

    def is_removable(self):
        """ This method decide is it is usefull to keep the node in the tree

        Return:
            True if the node can be removed from the tree, False otherwise.
        """
        return (AbstractNode.is_removable(self) and
                len(self.children) == 0 and
                len(self.waiting_nodes) == 0)

    def remove_child(self, node):
        """ This method remove a child node from this node it exists

        Arg:
            node<node>: the node to remove
        """
        self.children.pop(node.path_part, None)

    def unlock(self, owner=None):
        """ This method unlock the current node if locked and also unlock
            every locked children.

        Arg:
            owner<node>: the owner of the lock.  If the node is locked by
                another owner, the unlocking process will fail.
        """
        if owner is None:
            owner = self

        if self.lock_owner is not owner:
            return

        AbstractNode.unlock(self, owner)

        for child in self.children.values():
            child.unlock(owner)

        self.locked_children = 0

    def has_children_unlocked(self):
        """ This method returns True if at least one children is not locked.
            False otherwise.
        """
        return self.locked_children < len(self.children)

    def increment_children_locked_count(self):
        """ This method increments the counter of locked children """
        if self.locked_children < len(self.children):
            self.locked_children += 1

    def trigger_waiting_nodes(self):
        """ This method will trigger every waiting nodes """
        if len(self.waiting_nodes) > 0:
            nodes = list(self.waiting_nodes)
            del self.waiting_nodes[:]
            for node in nodes:
                node.trigger_waiting_task()

    def add_waiting_node(self, node, prior_node=False):
        """ This method add a node in the waiting list of the current node.

        Args:
            node: the node to add in the list
            prior_node<bool>: if set to True, the node will be added at the
                beggining of the list, otherwise at the end.
        """
        if self.lock_owner is not None and self.lock_owner is not self:
            self.lock_owner.add_waiting_node(node, prior_node)
        else:
            if prior_node:
                self.waiting_nodes.insert(0, node)
            else:
                self.waiting_nodes.append(node)

            node.waiting_for_node = self

    def remove_waiting_node(self, node=None):
        """ This method removes a node from the waiting list if the node
            exists in this list.

        Arg:
            node: the node to remove
        """
        if node is None:
            node = self

        if (self.waiting_for_node is not None and
                self.waiting_for_node is not self):
            self.waiting_for_node.remove_waiting_node(node)
        elif node in self.waiting_nodes:
            self.waiting_nodes.remove(node)
            node.waiting_for_node = None

    def set_prior(self, node=None):
        """ This method increase the priority of a node in the waiting list.

        arg:
            node: the node to put at the beggining of the list
        """
        if node is None:
            node = self

        if (self.waiting_for_node is not None and
                self.waiting_for_node is not self):
            self.waiting_for_node.set_prior(self)
        elif node in self.waiting_nodes:
            self.waiting_nodes.remove(node)
            self.waiting_nodes.insert(0, node)

    def traverse(self, explore=_accept_any, collect=_accept_any):
        """ This method will traverse the tree from the current node.

            The current node can be collected, but it won't explore parent
            nodes.

        Args:
            explore<fun>: a one argument<node> function that must return True
                if the directory node argument has to be explored
            collect<fun>: a one argument<node> function that must return True
                if the node argument has to be collected

        Return:
            a generator of nodes
        """
        if not explore(self):
            return

        nodes_stack = [(self, sorted(self.children.keys()), 0,)]

        while len(nodes_stack) > 0:
            node, node_keys, index = nodes_stack.pop()

            while index < len(node_keys):
                child_node = node.children[node_keys[index]]
                index += 1

                if not isinstance(child_node, DirectoryNode):
                    if collect(child_node):
                        yield child_node
                    continue

                nodes_stack.append((node, node_keys, index,))

                node = child_node
                node_keys = sorted(child_node.children.keys())
                index = 0

            if collect(node):
                yield node

    def traverse_only_directory_node(self):
        """ This method only collects directory node from this node

            The current node will be explored and every children and sub
            children will also be explored, but it won't explore parent
            nodes.

        Return:
            a generator of directory nodes
        """
        def collect(node):
            return isinstance(node, DirectoryNode)

        return self.traverse(collect=collect)

    def traverse_only_file_node(self):
        """ This method only collects file node from this node

            The current node will be explored and every children and sub
            children will also be explored, but it won't explore parent
            nodes.

        Return:
            a generator of file nodes
        """
        def collect(node):
            return isinstance(node, FileNode)

        return self.traverse(collect=collect)

    def get_or_insert_node(self,
                           path,
                           only_directory=False,
                           create=True,
                           index_saver=None):
        """ This method get or insert a node

        Args:
            path<string>: the complete path to get/insert in the tree
            only_directory<bool>: if this flag is set to True and if the path
                does not exist, the node inserted on the last part of the
                path will be a directory node in place of a file node.
            create<bool>: if set to True, the method will create the path
                in the tree if it does not exist
            index_saver<IndexSaver>: file node needs the index saver for
                the hash update, this arg can be None if the flag create
                is set to False or if the flag only_directory is set to
                True.

        Return:
            a node if the path exists or has been created, or None if the
            path does not exist and create flag is set to False.
        """

        parts = split_path(path)

        current_node = self
        for part_index in range(0, len(parts)):
            if parts[part_index] in current_node.children:
                current_node = current_node.children[parts[part_index]]
                continue

            if not create:
                return None

            # create a file node on the last part of the path
            if not only_directory and part_index == len(parts) - 1:
                new_node = FileNode(path_part=parts[part_index],
                                    index_saver=index_saver,
                                    parent=current_node,
                                    rel_path=path)
            else:
                new_node = DirectoryNode(parts[part_index], current_node)

            current_node.children[parts[part_index]] = new_node
            current_node = new_node

        return current_node


class FileNode(AbstractNode):
    """ This class represent a file node.  This kind of node is always a
        leaf node.  It contains the hashes informations (local or remote)
        linked to a file.  If both hashes are set to None, the node
        can be removed from the tree.

    Attributes:
        local_md5<string>: the local md5 hash.
        remote_md5<string>: the remote md5 hash.
        waiting_sync_node<node>: a parent node waiting for this node to be
            unlocked.
        self_waiting<bool>: if set to True, it means the current node is
            waiting for itself to be unlocked.
        do_invalidate_local<bool>: if set to True, it means the local hash
            has to be set to None has soon as the node will be unlocked.
        do_invalidate_remote<bool>: if set to True, it means the remote hash
            has to be set to None has soon as the node will be unlocked.
        index_saver<IndexSaver>: an instance of an index saver, it is suppose
            to have a method trigger_save without any argument.  This
            method will be called on every update of any hash.
        rel_path<string>: the relative path inside of the container.  This is
            the original path used at the insertion.
        visited<bool>: it is a coloring flag used by the sync task.
    """

    def __init__(self, path_part, index_saver, parent, rel_path):
        AbstractNode.__init__(self, path_part, parent)
        self.local_md5 = None
        self.remote_md5 = None
        self.waiting_sync_node = None
        self.self_waiting = False
        self.do_invalidate_local = False
        self.do_invalidate_remote = False
        self.index_saver = index_saver
        self.rel_path = rel_path
        self.visited = False

    def is_removable(self):
        """ This method decide is it is usefull to keep the node in the tree

        Return:
            True if the node can be removed from the tree, False otherwise.
        """
        return (AbstractNode.is_removable(self) and
                self.waiting_sync_node is None and
                not self.self_waiting and
                self.local_md5 is None and
                self.remote_md5 is None)

    def remove_child(self, node):
        """ this node is a leaf node and can't store any child node """
        pass

    def unlock(self, owner=None):
        """ this method unlock the node and trigger the most prior node if
            there is any.

        Arg:
            node<node>: the owner lock, if this arg is set to none, the owner
                will be set to self.
        """
        if owner is None:
            owner = self

        if self.lock_owner is not owner:
            return

        AbstractNode.unlock(self, owner)

        if self.do_invalidate_local:
            self.local_md5 = None
            self.do_invalidate_local = False

        if self.do_invalidate_remote:
            self.remote_md5 = None
            self.do_invalidate_remote = False

    def trigger_waiting_nodes(self):
        """ This method will trigger the most prior waiting node """
        if self.self_waiting:
            self.self_waiting = False
            self.trigger_waiting_task()
        elif self.waiting_sync_node is not None:
            node = self.waiting_sync_node
            self.waiting_sync_node = None
            node.trigger_waiting_task()

    def add_waiting_node(self, node, prior_node=False):
        """ add a node waiting for this node to be unlocked.

            At most two nodes can wait on a file node, itself and a parent
            directory.

        Args:
            node<node>: the node waiting for the current node.
            prior_node<bool>: set the priority in front of the other waiting
                node.  If set True, the node will be the first to be
                triggered.
        """
        if node is self:
            if self.waiting_sync_node is None:
                self.self_waiting = True
                self.waiting_for_node = self
            elif prior_node:
                self.waiting_sync_node.remove_waiting_node(self)
                self.self_waiting = True
                self.waiting_for_node = self
            else:
                self.waiting_sync_node.add_waiting_node(self)
        else:
            self.waiting_sync_node = node
            node.waiting_for_node = self

            if self.self_waiting and prior_node:
                self.waiting_sync_node.add_waiting_node(self)
                self.self_waiting = False

    def remove_waiting_node(self, node=None):
        """This method remove a node waiting for this node to be unlocked

        Arg:
            owner<node>: the node to remove.  If set to None, take the
                self node.
        """
        if node is None:
            node = self

        if (self.waiting_for_node is not None and
                self.waiting_for_node is not self):
            self.waiting_for_node.remove_waiting_node(node)
        elif node is self:
            self.self_waiting = False
            self.waiting_for_node = None
        elif node is self.waiting_sync_node:
            self.waiting_sync_node.waiting_for_node = None
            self.waiting_sync_node = None

    def set_prior(self, node=None):
        """ This method set the argument node as the most prior in the
            waiting nodes.

        Arg:
            owner<node>: the node to prioritize.  If set to None, take the
                self node.
        """
        if node is None:
            node = self

        if (self.waiting_for_node is not None and
                self.waiting_for_node is not self):
            self.waiting_for_node.set_prior(self)
        elif node is self:
            if not self.self_waiting and self.waiting_sync_node is not None:
                self.waiting_sync_node.remove_waiting_node(self)
                self.self_waiting = True
                self.waiting_for_node = self

        elif node is self.waiting_sync_node:
            if self.self_waiting:
                self.waiting_sync_node.add_waiting_node(self)
                self.self_waiting = False

    def set_hash(self, local_md5, remote_md5, trigger=True):
        """ This method set a new value to the hashes

        Args:
            local_md5<string>: the local md5 hash
            remote_md5<string>: the remote md5 hash
            trigger<bool>: if set to True, the index saver will be triggered
        """
        if self.local_md5 == local_md5 and self.remote_md5 == remote_md5:
            return

        self.local_md5 = local_md5
        self.remote_md5 = remote_md5

        if trigger and self.index_saver is not None:
            self.index_saver.trigger_save()

    def invalidate_local(self):
        """ This method invalidate the local hash """
        if self.is_locked():
            self.do_invalidate_local = True
        else:
            self.local_md5 = None

    def invalidate_remote(self):
        """ This method invalidate the remote hash """
        if self.is_locked():
            self.do_invalidate_remote = True
        else:
            self.remote_md5 = None

    def is_invalidate_local(self):
        """ This method return True is the local hash is not valid """
        if self.is_locked():
            return self.do_invalidate_local
        else:
            return self.local_md5 is None

    def is_invalidate_remote(self):
        """ This method return True is the remote hash is not valid """
        if self.is_locked():
            return self.do_invalidate_remote
        else:
            return self.remote_md5 is None

    def traverse_only_directory_node(self):
        """ This method will returns an empty generator, because no diretory
            node is accessible from this node
        """
        return
        yield

    def traverse_only_file_node(self):
        """ This method will returns a generator with only one node, the
            current node, because no other file node is accessible from here
        """
        yield self
        return
