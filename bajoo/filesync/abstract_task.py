#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import errno
import hashlib
import logging
import os
import shutil
import sys
import time

from ..common.strings import ensure_unicode
from ..encryption.errors import ServiceStoppingError

_logger = logging.getLogger(__name__)


class Target(object):
    """Compatibility class between new node format and old Task classes."""
    def __init__(self, index_tree, node):
        """

        Args:
            index_tree (IndexTree): index tree of the container.
            node (FileNode): file node member of the index tree. It's the
                target.
        """
        self._index_tree = index_tree
        self.node = node

        self.rel_path = node.get_full_path()
        self.local_md5, self.remote_md5 = node.get_hashes()

    def set_hash(self, local_hash, remote_hash):
        """Set hashes values of a FileNode."""
        with self._index_tree.lock:
            self.node.set_hashes(local_hash, remote_hash)

    def release(self):
        """Release the node.

        Note:
            The index tree lock must be acquired by the caller.
        """
        self.node.release()


class _Task(object):
    """Class representing a sync task.

    A task is executed in a separated thread (by the task_consumer service).
    The method `__call__()` will be called that in a I/O-bound thread and
    returns a Promise. In practice, the task can be executed in several steps
    (network and encryption parts).
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, container, target, local_container,
                 expected_target_count=1):
        """
        Args:
            container (Container): used to performs upload and download
                requests.
            target (List<str>): a list of target path, relative to
                the container.
            local_container (LocalContainer): local container. It will be used
                only to acquire, update and release index fragments.
            expected_target_count: define the minimal number of needed target
                in the target list.
        """
        if target is None or len(target) < expected_target_count:
            raise Exception('This task need at least \'%s\' Target, '
                            'got \'%s\'' % (expected_target_count,
                                            len(target) if target else 0))

        self._index_acquired = False
        self.container = container
        self.target_list = []
        self.local_container = local_container
        self.local_path = local_container.model.path
        self.nodes = []

        for t in target:
            node = self.local_container.index_tree.get_node_by_path(t)
            self.nodes.append(Target(self.local_container.index_tree, node))

        if sys.platform in ['win32', 'cygwin', 'win64']:
            for t in target:
                t = ensure_unicode(t)
                self.target_list.append(t.replace('\\', '/'))
        else:
            for t in target:
                t = ensure_unicode(t)
                self.target_list.append(t)

    def _log(self, logger, msg, *args, **kwargs):
        """Log a message with Task ID."""
        level = kwargs.pop('level', 5)
        logger.log(level, 'Task %s: ' + msg, hex(id(self)), *args, **kwargs)

    def __repr__(self):
        encoded_string = []

        for string in self.target_list:
            if not isinstance(string, str):
                encoded_string.append(string.encode('utf-8'))
            else:
                encoded_string.append(string)

        target_string = ', '.join(encoded_string)

        if not isinstance(self.local_path, str):
            # Python 2 with type unicode.
            local_path = self.local_path.encode('utf-8')
        else:
            local_path = self.local_path

        s = '<Task %s (%s) local_path=%s>' % (self.get_type().upper(),
                                              target_string, local_path)
        return s

    def __call__(self):
        """Execute the task.

        The task will be added to the ref task index during the initialization
        phase.

        Returns:
            Promise<None>: Succeed when the task is done. Can fails if an
                error occurs.
        """

        self._log(_logger, 'Prepare task %s', self)

        self._index_acquired = True

        # Execution of the _apply_task generator
        # This code is a 'yield from', compatible python 2 and 3.
        gen = self._apply_task()
        try:
            from ..promise import is_thenable

            try:
                result = next(gen)
            except StopIteration:
                result = None

            while is_thenable(result):
                try:
                    value = yield result
                except Exception:
                    try:
                        result = gen.throw(*sys.exc_info())
                    except StopIteration:
                        result = None
                else:
                    try:
                        result = gen.send(value)
                    except StopIteration:
                        result = value
        except Exception as error:
            self._manage_error(error)
        finally:
            gen.close()
            self._release_index()
            self._log(_logger, 'Task %s Done.', self, level=logging.DEBUG)

        yield None  # return

    @staticmethod
    def get_type():
        """Get the task type

        The purpose of this method is to allow to get a human readable type
        on the message printed during the execution of abstract method

        A child class should always override this method

        Returns:
            str: the task type
        """

        return "abstract"

    def _release_index(self):
        if self._index_acquired:
            tree = self.local_container.index_tree
            with tree.lock:
                for target in self.nodes:
                    target.release()
            self._index_acquired = False

    def _manage_error(self, error):
        """Catch all error happened during the task execution.

        Some of theses errors are uncommon, but acceptable situations, and
        should be ignored.
        """
        if not isinstance(error, ServiceStoppingError):
            self._log(_logger, 'Exception', level=logging.ERROR, exc_info=True)
        raise error

    @abc.abstractmethod
    def _apply_task(self):
        """Execute the business part of the task"""
        return

    @staticmethod
    def _compute_md5_hash(file_content):
        """Compute the md5 hash of a file

        Note that the file cursor is not reset to the beginning of the file,
        neither before nor after the hash computation.

        Args:
            file_content (file-like): file to check.
        Returns:
            str: md5 hash
        """
        d = hashlib.md5()
        for buf in file_content:
            d.update(buf)
        return d.hexdigest()

    def _write_downloaded_file(self, file_content, target):
        """Write the downloaded file on the disk and close it.

        Returns:
            str: the local md5 hash
        """
        abs_path = os.path.join(self.local_path, target.rel_path)
        md5_hash = self._compute_md5_hash(file_content)
        file_content.seek(0)
        try:
            os.makedirs(os.path.dirname(abs_path))
        except (IOError, OSError) as e:
            if e.errno != errno.EEXIST:
                raise
        with open(abs_path, 'wb') as dest_file, file_content:
            shutil.copyfileobj(file_content, dest_file)

        return md5_hash

    def _generate_conflicting_file_name(self, target):
        """Return a unique file name resulting to be used in a conflict

        In a conflict context, a task needs a way to generate a unique
        file name.

        Returns:
            str: a unique conflict name
        """

        target_path = os.path.join(self.local_path, target.rel_path)
        time_tuple = time.localtime(os.path.getmtime(target_path))
        time_string = time.strftime("%d_%b_%Y_%H_%M", time_tuple)

        prefix_name, ext = os.path.splitext(target.rel_path)
        new_name = "%s (conflict %s)%s" % (prefix_name, time_string, ext)

        counter = 1

        while os.path.exists(os.path.join(self.local_path, new_name)):
            new_name = "%s (conflict %s %s)%s" % (prefix_name, str(counter),
                                                  time_string, ext)
            counter += 1

        return new_name

    def _create_push_task(self, rel_path):
        from ..index.file_node import FileNode
        from ..index.hint_builder import HintBuilder
        tree = self.local_container.index_tree

        # create the node.
        HintBuilder.apply_modified_event_from_path(tree,
                                                   HintBuilder.SCOPE_LOCAL,
                                                   rel_path, None, FileNode)

    def _create_a_remove_task(self, target):
        from ..index.hint_builder import HintBuilder

        with self.local_container.index_tree.lock:
            HintBuilder.apply_deleted_event(HintBuilder.SCOPE_REMOTE,
                                            target.node)

    def _create_added_remote_task(self, target):
        from ..index.hint_builder import HintBuilder

        with self.local_container.index_tree.lock:
            HintBuilder.apply_modified_event(HintBuilder.SCOPE_REMOTE,
                                             target.node)
