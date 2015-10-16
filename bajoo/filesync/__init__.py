# -*- coding: utf-8 -*-

"""Synchronize files between local filesystem and remote Bajoo servers.

The module contains a thread dedicated to comparison and verification of files.
It executes a list of "tasks" created by the 6 public methods:
 - added_remote_files
 - changed_remote_files
 - removed_remote_files
 - added_local_files
 - changed_local_files
 - removed_local_files
 - moved_local_files

When calling one of theses methods, a task is added to performs the needed
operation to keep local and remote folders synced.
If the tasks need to works on many files (eg: a task on a folder containing
subfolders), it can be executed partially and "splitted" in many small tasks.

The tasks send network requests, ask for encryption, and so will often wait
asynchronous operations. Many tasks will be executed in parallel.

Each task take in parameters the local container. It will be used to retrieve
the hashes corresponding to the concerned files.
When done, it generates a dict containing the new values for theses hashes. If
the dict is empty (or if some items are missing), the original hash values are
removed. When an error occurs, the new index fragment is not generated. In this
case, the original hash values are not modified.
The Future returns True or False, according to the success of the operation.
The task should be executed again latter if it returns False.
Sometimes, a task is ignored (duplicate tasks); In this case, the function
doesn't returns a Future, but directly None.
"""

import errno
from functools import partial
import hashlib
import itertools
import logging
import os
import shutil
import sys

from ..network.errors import HTTPNotFoundError
from ..common import config
from ..common.future import Future, patch_dec, wait_all, then, resolve_rec
from .filepath import is_path_allowed, is_hidden
from ..common.i18n import _
from ..promise import ThreadPoolExecutor


_logger = logging.getLogger(__name__)

_thread_pool = ThreadPoolExecutor(max_workers=5)


class _Task(object):
    """Class representing a sync task.

    A task is executed in a separated thread (in the _thread_pool). The method
    `start()` will start that thread and returns a Future. In practice, the
    task can be executed in several steps (network and encryption parts), and
    can be split in many subtasks (for SYNC tasks).
    """

    # Type of tasks
    LOCAL_ADD = 'local_add'
    LOCAL_CHANGE = 'local_change'
    LOCAL_DELETION = 'local_deletion'
    REMOTE_ADD = 'remote_add'
    REMOTE_CHANGE = 'remote_change'
    REMOTE_DELETION = 'remote_deletion'
    SYNC = 'sync'

    def __init__(self, type, container, target, local_container,
                 display_error_cb):
        """
        Args:
            type (str): One of the 8 type declared above.
            container (Container): used to performs upload and download
                requests.
            target (str): path of the target, relative the the container.
            local_container (LocalContainer): local container. It will be used
                only to acquire, update and release index fragments.
            display_error_cb (callable)
        """
        self._index_acquired = False
        self.type = type
        self.container = container
        self.target = target
        self.local_container = local_container
        self.local_path = local_container.model.path
        self.index_fragment = {}
        self.local_md5 = None
        self.remote_md5 = None
        self.display_error_cb = display_error_cb

        if sys.platform in ['win32', 'cygwin', 'win64']:
            self.target = self.target.replace('\\', '/')

        # If set, list of tasks who've failed.
        self._task_errors = None

    def __repr__(self):
        s = ('<Task %s %s local_path=%s>' %
             (self.type.upper(), self.target, self.local_path))
        if not isinstance(s, str):
            # Python 2 with type unicode.
            s = s.encode('utf-8')
        return s

    def start(self, parent_path=None):
        """Register the task and execute it.

        The task will be added to the ref task index.

        Args:
            parent_path (str, optional): if ste, target path of the parent
                task. It indicates the parent task allow this one to "acquire"
                fragments of folder owner by itself.
        """
        delayed_start = Future()  # Future used in case of delayed start
        path, item = self.local_container.acquire_index(
            self.target, (self, None),
            partial(self._delayed_start, delayed_start),
            bypass_folder=parent_path)
        if path is not None:  # The path is not available.
            _logger.debug('Resource path acquired by another task; '
                          'waiting for %s..' % self.target)
            # TODO: detect if it's possible to merge the 2 events.
            return delayed_start

        self._index_acquired = True
        if item:
            self.index_fragment = item
            self.local_md5, self.remote_md5 = item.get(self.target,
                                                       (None, None))

        future = resolve_rec(_thread_pool.submit(self._apply_task))
        future = future.then(None, self._manage_error)
        future = future.then(self._release_index)
        return future.then(lambda _none: self._task_errors)

    def _delayed_start(self, future):
        """Execute a delayed start() call.

        A start() call has been delayed, as the fragment index was not
        available at the moment it was requested.

        Args:
            future (Future): empty, non started future. It will be notified
                before start() and will receive the result of start().
        """
        if not future.set_running_or_notify_cancel():
            return  # The task has been cancelled !
        f = self.start()
        if f:
            then(f, future.set_result, future.set_exception)
        else:
            future.set_result(None)

    def _release_index(self, result=None):
        if self._index_acquired:
            if sys.platform in ['win32', 'cygwin', 'win64'] and result:
                result = {key.replace('\\', '/'): value
                          for (key, value) in result.items()}
            self.local_container.release_index(self.target, result)
            self._index_acquired = False

    def _manage_error(self, error):
        """Catch all error happened during the task execution.

        Some of theses errors are uncommon, but acceptable situations, and
        should be ignored.
        """
        if isinstance(error, HTTPNotFoundError):
            if self.type == _Task.LOCAL_DELETION:
                _logger.debug('The file to delete is already gone:'
                              'nothing to do.')
                return {}

        _logger.exception('Exception on filesync task:')

        if not self._task_errors:
            self._task_errors = []
        self._task_errors.append(self)

        if self.container.error:
            self.display_error_cb(
                _("Error during the sync of the \"%s\" container:\n%s")
                % (self.container.name, error))
            raise self.container.error
        else:
            self.display_error_cb(
                _("Error during sync of the file \"%s\" "
                  "in the \"%s\" container:\n%s")
                % (self.target, self.container.name, error))
        return None

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        if self.type in (_Task.LOCAL_ADD, _Task.LOCAL_CHANGE):
            src_path = os.path.join(self.local_path, self.target)

            file_content = None
            try:
                file_content = open(src_path, 'rb')
            except (IOError, OSError) as err:
                if err.errno == errno.ENOENT and self.type == _Task.LOCAL_ADD:
                    _logger.debug("The file is gone before we've done"
                                  " anything.")
                    return {}
                raise
            try:
                md5 = self._compute_md5_hash(file_content)
                if self.remote_md5 and md5 == self.local_md5:  # Nothing to do
                    _logger.debug('local md5 hash has not changed. '
                                  'No need to upload.')
                    file_content.close()
                    return {self.target: (self.local_md5, self.remote_md5)}
                file_content.seek(0)
            except:
                if file_content:
                    file_content.close()
                raise

            def callback(metadata):
                return {self.target: (md5, metadata['hash'])}

            f = self.container.upload(self.target, file_content)
            return f.then(callback)
        elif self.type == _Task.LOCAL_DELETION:
            # Delete remote file
            return self.container.remove_file(self.target).then(lambda _: {})
        elif self.type in (_Task.REMOTE_ADD, _Task.REMOTE_CHANGE):

            if self.type == _Task.REMOTE_ADD:
                # Make folder
                try:
                    abs_path = os.path.join(self.local_path, self.target)
                    os.makedirs(os.path.dirname(abs_path))
                except (IOError, OSError) as e:
                    if e.errno != errno.EEXIST:
                        raise e

            def callback(result):
                metadata, file_content = result
                remote_md5 = metadata['hash']
                future = _thread_pool.submit(self._write_downloaded_file,
                                             file_content)
                return future.then(lambda local_md5: {
                    self.target: (local_md5, remote_md5)})

            return self.container.download(self.target).then(callback)
        elif self.type == _Task.REMOTE_DELETION:
            # Delete local
            src_path = os.path.join(self.local_path, self.target)

            try:
                os.remove(src_path)
            except (IOError, OSError) as e:
                if e.errno != errno.ENOENT:
                    _logger.debug('The file to delete is'
                                  ' not present on the'
                                  'disk: nothing to do.')
                    raise
            return {}
        else:  # SYNC
            src_path = os.path.join(self.local_path, self.target)
            subtasks = []

            for name in os.listdir(src_path):
                abs_path = os.path.join(src_path, name)
                rel_path = os.path.relpath(abs_path, self.local_path)
                task = None

                if config.get('exclude_hidden_files') and is_hidden(abs_path):
                    continue
                if os.path.isdir(abs_path):
                    self.index_fragment = {
                        k: v for (k, v) in self.index_fragment.items()
                        if not k.startswith('%s/' % rel_path)}
                    task = _Task(_Task.SYNC, self.container, rel_path,
                                 self.local_container, self.display_error_cb)
                else:
                    if not is_path_allowed(rel_path):
                        continue

                    if rel_path in self.index_fragment:
                        # TODO: don't log when file is not modified !
                        del self.index_fragment[rel_path]
                        task = _Task(_Task.LOCAL_CHANGE, self.container,
                                     rel_path, self.local_container,
                                     self.display_error_cb)
                    else:
                        task = _Task(_Task.LOCAL_ADD, self.container,
                                     rel_path, self.local_container,
                                     self.display_error_cb)

                if task:
                    subtasks.append(task.start(parent_path=self.target))

            # locally removed items, present in the index, but not in local.
            for child_path in self.index_fragment:
                task = _Task(_Task.LOCAL_DELETION, self.container, child_path,
                             self.local_container, self.display_error_cb)
                subtasks.append(task.start(parent_path=self.target))

            self._release_index()

            if subtasks:
                def all_tasks_done(results):
                    failed_tasks = itertools.chain(*filter(None, results))
                    failed_tasks = list(failed_tasks)
                    if failed_tasks:
                        self._task_errors = failed_tasks
                    return None

                return wait_all(subtasks).then(all_tasks_done)
            else:
                return None

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

    def _write_downloaded_file(self, file_content):
        """Write the downloaded file on the disk.

        Returns:
            str: the local md5 hash
        """
        abs_path = os.path.join(self.local_path, self.target)
        md5_hash = self._compute_md5_hash(file_content)
        file_content.seek(0)
        with open(abs_path, 'wb') as dest_file, file_content:
            shutil.copyfileobj(file_content, dest_file)

        return md5_hash


@patch_dec
def added_remote_files(container, local_container, filename, display_error_cb):
    task = _Task(_Task.REMOTE_ADD, container, filename, local_container,
                 display_error_cb)
    return task.start()


@patch_dec
def changed_remote_files(container, local_container, filename,
                         display_error_cb):
    task = _Task(_Task.REMOTE_CHANGE, container, filename, local_container,
                 display_error_cb)
    return task.start()


@patch_dec
def removed_remote_files(container, local_container, filename,
                         display_error_cb):
    task = _Task(_Task.REMOTE_DELETION, container, filename, local_container,
                 display_error_cb)
    return task.start()


@patch_dec
def added_local_files(container, local_container, filename, display_error_cb):
    """Tells that a new file as been created and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the file created, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_ADD, container, filename, local_container,
                 display_error_cb)
    return task.start()


@patch_dec
def changed_local_files(container, local_container, filename,
                        display_error_cb):
    """Tells that a file has been modified and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the modified file, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_CHANGE, container, filename, local_container,
                 display_error_cb)
    return task.start()


@patch_dec
def removed_local_files(container, local_container, filename,
                        display_error_cb):
    """Tells that a file has been deleted and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the deleted file, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_DELETION, container, filename, local_container,
                 display_error_cb)
    return task.start()


def moved_local_files(container, local_container, src_filename, dest_filename,
                      display_error_cb):
    """Tells that a file has been moved, and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        src_filename (str): source filename of the moved file, relative to
            base_path.
        dest_filename (str): destination filename of the movedfile, relative to
            base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    # TODO: optimization: move the file server-side.

    def join_results(results):
        results = filter(None, results)
        if results:
            if len(results) > 1:
                return results[0] + results[1]
            else:
                return results[0]

    return wait_all([
        _Task(_Task.LOCAL_DELETION, container, src_filename,
              local_container, display_error_cb).start(),
        _Task(_Task.LOCAL_ADD, container, dest_filename,
              local_container, display_error_cb).start()
    ]).then(join_results)


@patch_dec
def sync_folder(container, local_container, folder_path, display_error_cb):
    """Sync a local folder

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): path of the directory, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.SYNC, container, folder_path, local_container,
                 display_error_cb)
    return task.start()
