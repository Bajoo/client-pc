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
from ..common.strings import ensure_unicode
from ..network.errors import HTTPEntityTooLargeError
from ..encryption.errors import PassphraseAbortError
from .exception import RedundantTaskInterruption

_logger = logging.getLogger(__name__)


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
        self.display_error_cb = display_error_cb
        self._parent_path = parent_path
        self.nodes = []

        if sys.platform in ['win32', 'cygwin', 'win64']:
            for t in target:
                t = ensure_unicode(t)
                self.target_list.append(t.replace('\\', '/'))
        else:
            for t in target:
                t = ensure_unicode(t)
                self.target_list.append(t)

        # list of tasks who've failed.
        # If there is no error, it's an empty list.
        self._task_errors = []
        self.error = None

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
            Promise<list>: List of task in error. If there is no error, returns
                an empty list.
        """

        _logger.debug('Prepare task %s' % self)

        try:
            self.nodes = yield self.local_container.index.acquire(
                self.target_list,
                self)
        except RedundantTaskInterruption:
            yield self._task_errors
            return

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

    def _release_index(self):
        if self._index_acquired:
            self.local_container.index.release(self.target_list, self)
            self._index_acquired = False

    def _manage_error(self, error):
        """Catch all error happened during the task execution.

        Some of theses errors are uncommon, but acceptable situations, and
        should be ignored.
        """

        _logger.exception('Exception on %s task:' % self.get_type())

        self._task_errors.append(self)

        self.error = error

        if not isinstance(error, PassphraseAbortError) and \
                not isinstance(error, HTTPEntityTooLargeError):
            if self.container.error:
                self.display_error_cb(
                    _('Error during the sync of the "%(name)s" container:'
                      '\n%(error)s')
                    % {'name': self.container.name, 'error': error})
                raise self.container.error
            else:
                target_string = ', '.join(str(x) for x in self.target_list)
                self.display_error_cb(
                    _('Error during sync of the file(s) "%(filename)s" '
                      'in the "%(name)s" container:\n%(error)s')
                    % {'filename': target_string, 'name': self.container.name,
                       'error': error})

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
        time_string = time.strftime("%d_%b_%Y_%H_%M", time_tuple)

        prefix_name, ext = os.path.splitext(target.rel_path)
        new_name = "%s (conflict %s)%s" % (prefix_name, time_string, ext)

        counter = 1

        while os.path.exists(os.path.join(self.local_path, new_name)):
            new_name = "%s (conflict %s %s)%s" % (prefix_name, str(counter),
                                                  time_string, ext)
            counter += 1

        return new_name
