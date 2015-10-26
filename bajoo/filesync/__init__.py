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
The Promise returns True or False, according to the success of the operation.
The task should be executed again latter if it returns False.
Sometimes, a task is ignored (duplicate tasks); In this case, the function
doesn't returns a Promise, but directly None.
"""

import errno
import hashlib
import itertools
import logging
import os
import shutil
import sys

from ..network.errors import HTTPNotFoundError
from ..common import config
from .filepath import is_path_allowed, is_hidden
from ..common.i18n import _
from ..promise import Promise
from .task_consumer import add_task, start, stop


_logger = logging.getLogger(__name__)


# TODO: the module should be started and stopped by the caller.
# start the task_consumer service
import atexit
start()
atexit.register(stop)


class _Task(object):
    """Class representing a sync task.

    A task is executed in a separated thread (by the task_consumer service).
    The method `__call__()` will be called that in a I/O-bound thread and
    returns a Promise. In practice, the task can be executed in several steps
    (network and encryption parts), and can be split in many subtasks (for
    SYNC tasks).
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
                 display_error_cb, parent_path=None):
        """
        Args:
            type (str): One of the 8 type declared above.
            container (Container): used to performs upload and download
                requests.
            target (str): path of the target, relative the the container.
            local_container (LocalContainer): local container. It will be used
                only to acquire, update and release index fragments.
            display_error_cb (callable)
            parent_path (str, optional): if set, target path of the parent
                task. It indicates the parent task allow this one to "acquire"
                fragments of folder owner by itself.
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
        self._parent_path = parent_path

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

    def __call__(self):
        """Execute the task.

        The task will be added to the ref task index during the initialization
        phase.
        """

        _logger.debug('Prepare task %s' % self)
        # Initialization: we acquire the index
        p = self.local_container.acquire_index(
            self.target, (self, None), bypass_folder=self._parent_path)
        item = yield p

        self._index_acquired = True
        if item:
            self.index_fragment = item
            self.local_md5, self.remote_md5 = item.get(self.target,
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
                        gen.throw(*sys.exc_info())
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
                _('Error during the sync of the "%(name)s" container:'
                  '\n%(error)s')
                % {'name': self.container.name, 'error': error})
            raise self.container.error
        else:
            self.display_error_cb(
                _('Error during sync of the file "%(filename)s" '
                  'in the "%(name)s" container:\n%(error)s')
                % {'filename': self.target, 'name': self.container.name,
                   'error': error})
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
                    yield {}
                    return
                raise
            try:
                md5 = self._compute_md5_hash(file_content)
                if self.remote_md5 and md5 == self.local_md5:  # Nothing to do
                    _logger.debug('local md5 hash has not changed. '
                                  'No need to upload.')
                    file_content.close()
                    yield {self.target: (self.local_md5, self.remote_md5)}
                    return
                file_content.seek(0)
            except:
                if file_content:
                    file_content.close()
                raise

            metadata = yield self.container.upload(self.target, file_content)
            yield {self.target: (md5, metadata['hash'])}
            return
        elif self.type == _Task.LOCAL_DELETION:
            # Delete remote file
            yield self.container.remove_file(self.target)
            yield {}
            return
        elif self.type in (_Task.REMOTE_ADD, _Task.REMOTE_CHANGE):

            if self.type == _Task.REMOTE_ADD:
                # Make folder
                try:
                    abs_path = os.path.join(self.local_path, self.target)
                    os.makedirs(os.path.dirname(abs_path))
                except (IOError, OSError) as e:
                    if e.errno != errno.EEXIST:
                        raise e

            x = self.container.download(self.target)
            result = yield x

            metadata, file_content = result
            remote_md5 = metadata['hash']
            local_md5 = self._write_downloaded_file(file_content)
            yield {self.target: (local_md5, remote_md5)}
            return
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
            yield {}
            return
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
                                 self.local_container, self.display_error_cb,
                                 parent_path=self.target)
                else:
                    if not is_path_allowed(rel_path):
                        continue

                    if rel_path in self.index_fragment:
                        # TODO: don't log when file is not modified !
                        del self.index_fragment[rel_path]
                        task = _Task(_Task.LOCAL_CHANGE, self.container,
                                     rel_path, self.local_container,
                                     self.display_error_cb,
                                     parent_path=self.target)
                    else:
                        task = _Task(_Task.LOCAL_ADD, self.container,
                                     rel_path, self.local_container,
                                     self.display_error_cb,
                                     parent_path=self.target)

                if task:
                    subtasks.append(add_task(task, priority=True))

            # locally removed items, present in the index, but not in local.
            for child_path in self.index_fragment:
                task = _Task(_Task.LOCAL_DELETION, self.container, child_path,
                             self.local_container, self.display_error_cb,
                             parent_path=self.target)
                subtasks.append(add_task(task, priority=True))

            self._release_index()

            if subtasks:
                # TODO: retrieve all errors.
                # The current behavior is to return the first error
                # encountered, discarding the other results.
                # We need to get all results and errors , no matter who many
                # errors are raised.
                results = yield Promise.all(subtasks)
                failed_tasks = itertools.chain(*filter(None, results))
                failed_tasks = list(failed_tasks)
                if failed_tasks:
                    self._task_errors = failed_tasks
            yield None
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


def added_remote_files(container, local_container, filename, display_error_cb):
    task = _Task(_Task.REMOTE_ADD, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


def changed_remote_files(container, local_container, filename,
                         display_error_cb):
    task = _Task(_Task.REMOTE_CHANGE, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


def removed_remote_files(container, local_container, filename,
                         display_error_cb):
    task = _Task(_Task.REMOTE_DELETION, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


def added_local_files(container, local_container, filename, display_error_cb):
    """Tells that a new file as been created and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the file created, relative to base_path.
    Returns:
        Promise<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_ADD, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


def changed_local_files(container, local_container, filename,
                        display_error_cb):
    """Tells that a file has been modified and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the modified file, relative to base_path.
    Returns:
        Promise<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_CHANGE, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


def removed_local_files(container, local_container, filename,
                        display_error_cb):
    """Tells that a file has been deleted and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the deleted file, relative to base_path.
    Returns:
        Promise<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_DELETION, container, filename, local_container,
                 display_error_cb)
    return add_task(task)


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
        Promise<boolean>: True if the task is successful; False if an error
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

    return Promise.all([
        add_task(_Task(_Task.LOCAL_DELETION, container, src_filename,
                       local_container, display_error_cb)),
        add_task(_Task(_Task.LOCAL_ADD, container, dest_filename,
                       local_container, display_error_cb))
    ]).then(join_results)


def sync_folder(container, local_container, folder_path, display_error_cb):
    """Sync a local folder

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): path of the directory, relative to base_path.
    Returns:
        Promise<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.SYNC, container, folder_path, local_container,
                 display_error_cb)
    return add_task(task)
