#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import hashlib
import logging
import os
import shutil
import sys
import time

from ..common.i18n import _
from ..promise import Promise
from ..network.errors import HTTPEntityTooLargeError

_logger = logging.getLogger(__name__)


class _Target(object):

    def __init__(self, rel_path):
        self.rel_path = rel_path
        self.local_md5 = None
        self.remote_md5 = None

    def __str__(self):
        # Python 2 with type unicode.
        if not isinstance(self.rel_path, str):
            return self.rel_path.encode('utf-8')

        return self.rel_path


class _Task(object):
    """Class representing a sync task.

    A task is executed in a separated thread (by the task_consumer service).
    The method `__call__()` will be called that in a I/O-bound thread and
    returns a Promise. In practice, the task can be executed in several steps
    (network and encryption parts), and can be split in many subtasks (for
    SYNC tasks).
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, container, target, local_container,
                 display_error_cb, parent_path=None, expected_target_count=1):
        """
        Args:
            container (Container): used to performs upload and download
                requests.
            target (List<str>): a list of target path, relative to
                the container.
            local_container (LocalContainer): local container. It will be used
                only to acquire, update and release index fragments.
            display_error_cb (callable)
            parent_path (str, optional): if set, target path of the parent
                task. It indicates the parent task allow this one to "acquire"
                fragments of folder owner by itself.
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
        self.index_fragment = {}
        self.display_error_cb = display_error_cb
        self._parent_path = parent_path

        if sys.platform in ['win32', 'cygwin', 'win64']:
            for t in target:
                self.target_list.append(_Target(t.replace('\\', '/')))
        else:
            for t in target:
                self.target_list.append(_Target(t))

        # If set, list of tasks who've failed.
        self._task_errors = None
        self.error = None

    def __repr__(self):
        targetString = ', '.join(str(x) for x in self.target_list)

        if not isinstance(self.local_path, str):
            # Python 2 with type unicode.
            local_path = self.local_path.encode('utf-8')
        else:
            local_path = self.local_path

        s = '<Task %s (%s) local_path=%s>' % (self.get_type().upper(),
                                              targetString, local_path)
        return s

    def __call__(self):
        """Execute the task.

        The task will be added to the ref task index during the initialization
        phase.
        """

        _logger.debug('Prepare task %s' % self)

        # sort the target by rel_path to avoid deadlock during index acquiring
        # for more details: see Dining philosophers problem
        promises_list = []
        deadlock_avoider_target_list = sorted(self.target_list,
                                              key=lambda t: t.rel_path)

        # Initialization: we acquire the index
        for target in deadlock_avoider_target_list:
            promises_list.append(self.local_container.acquire_index(
                target.rel_path,
                (self, None),
                bypass_folder=self._parent_path))

        item_list = yield Promise.all(promises_list)

        self._index_acquired = True
        self.index_fragment = {}
        for item in item_list:
            if item is None:
                continue

            self.index_fragment.update(item)

        for target in self.target_list:
            target.local_md5, target.remote_md5 = self.index_fragment.get(
                target.rel_path,
                (None, None))

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
            result = self._manage_error(error)
        finally:
            gen.close()

        self._release_index(result)

        yield self._task_errors  # return

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

    def _release_index(self, result=None):
        if self._index_acquired:
            if sys.platform in ['win32', 'cygwin', 'win64'] and result:
                result = {key.replace('\\', '/'): value
                          for (key, value) in result.items()}

            for target in self.target_list:
                tmp_result = None
                if result is not None:
                    if target.rel_path in result:
                        tmp_result = {}
                        tmp_result[target.rel_path] = result[target.rel_path]
                    else:
                        tmp_result = result

                self.local_container.release_index(target.rel_path, tmp_result)

            self._index_acquired = False

    def _manage_error(self, error):
        """Catch all error happened during the task execution.

        Some of theses errors are uncommon, but acceptable situations, and
        should be ignored.
        """

        _logger.exception('Exception on %s task:' % self.get_type())

        if not self._task_errors:
            self._task_errors = []
        self._task_errors.append(self)

        self.error = error

        if isinstance(error, HTTPEntityTooLargeError):
            self.local_container.status = \
                self.local_container.STATUS_QUOTA_EXCEEDED
            self.display_error_cb(_("Quota limit reached"))

        if self.container.error:
            self.display_error_cb(
                _('Error during the sync of the "%(name)s" container:'
                  '\n%(error)s')
                % {'name': self.container.name, 'error': error})
            raise self.container.error
        else:
            targetString = ', '.join(str(x) for x in self.target_list)
            self.display_error_cb(
                _('Error during sync of the file(s) "%(filename)s" '
                  'in the "%(name)s" container:\n%(error)s')
                % {'filename': targetString, 'name': self.container.name,
                   'error': error})
        return None

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
        """Write the downloaded file on the disk.

        Returns:
            str: the local md5 hash
        """
        abs_path = os.path.join(self.local_path, target.rel_path)
        md5_hash = self._compute_md5_hash(file_content)
        file_content.seek(0)
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
        time_string = time.strftime("%d_%b_%Y_%H:%M", time_tuple)

        prefix_name, ext = os.path.splitext(target.rel_path)
        new_name = prefix_name + "(conflict_" + time_string + ")" + ext

        counter = 1

        while os.path.exists(os.path.join(self.local_path, new_name)):
            new_name = prefix_name + \
                "(conflict" + str(counter) + "_" + time_string + ")" + ext
            counter += 1

        return new_name
