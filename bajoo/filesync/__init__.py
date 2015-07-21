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
The Future returns True or False, accoridng to the success of the operation.
The task should be executed again latter if it returns False.
Sometimes, a task is ignored (duplicate tasks); In this case, the function
doesn't returns a Future, but directly None.
"""

from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
import logging
import os

from ..network.errors import HTTPNotFoundError
from ..common.future import Future, patch_dec, wait_all

_logger = logging.getLogger(__name__)

_thread_pool = ThreadPoolExecutor(max_workers=1)


class _Task(object):
    """Class representing a sync task."""

    # Type of tasks
    LOCAL_ADD = 'local_add'
    LOCAL_CHANGE = 'local_change'
    LOCAL_MOVE = 'local_move'
    LOCAL_DELETION = 'local_deletion'
    REMOTE_ADD = 'remote_add'
    REMOTE_CHANGE = 'remote_change'
    REMOTE_DELETION = 'remote_deletion'
    SYNC = 'sync'

    def __init__(self, type, container, target, local_container):
        self.type = type
        self.container = container
        self.target = target
        self.local_container = local_container
        self.local_path = local_container.path
        self.local_md5 = None
        self.remote_md5 = None

    def __repr__(self):
        return ('<Task %s %s local_path=%s>' %
                (self.type.upper(), self.target, self.local_path))

    def start(self):
        """Register the task and execute it.

        The task will be added to the ref task index.
        """
        path, item = self.local_container.acquire_index(self.target,
                                                        (self, None))
        if path is not None:  # The path is not available.
            _logger.debug('Resource path acquired by another task; waiting ..')

            return item[1].then(lambda _: self.start(), lambda _: self.start())
            # TODO: detect if it's possible to merge the 2 events.

        if item:
            # TODO: save index fragment in case of multiples values.
            self.local_md5, self.remote_md5 = item.get(self.target,
                                                       (None, None))

        future = _thread_pool.submit(self.execute)
        self.local_container.update_index_owner(self.target, (self, future))
        return future

    def execute(self):
        """Execute the task (called in a dedicated thread).

        Returns:
            boolean: True if all is OK, False if there is an error. In case of
                error the task should be executed again (by the caller) after a
                short time, then the target should be excluded if the error
                persists.
        """
        result = None
        try:
            result = self._apply_task()
        except Exception as error:
            result = self._manage_error(error)
        finally:
            self.local_container.release_index(self.target, result)

        return result is not None

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

        # TODO: These errors should be reported to the user, and the
        # concerned files should be excluded of the sync for a period of
        # 24h if they keep failing.

        return None

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        if self.type in (_Task.LOCAL_ADD, _Task.LOCAL_CHANGE):
            src_path = os.path.join(self.local_path, self.target)

            # TODO: upload should do the encryption, the upload, and check the
            # integrity ! The 4 steps below:
            # - encrypt
            # - check remote_md5
            # - upload
            # - confirm upload

            file_content = None
            try:
                file_content = open(src_path)
            except (IOError, OSError) as err:
                if err.errno == errno.ENOENT and self.type == _Task.LOCAL_ADD:
                    # The file is gone before we've done anything.
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

            self.container.upload(self.target, file_content)
            return {self.target: (md5, md5)}
            # TODO: check upload error
            # TODO: return value {self.target: (md5, new_remote_from_uplaod)}
        elif self.type == _Task.LOCAL_DELETION:
            # Delete remote file
            # TODO: we should avoid to resolve future with result()
            self.container.remove_file(self.target).result()
            return {}
        elif self.type in (_Task.REMOTE_ADD, _Task.REMOTE_CHANGE):

            # download
            # check remote_md5
            #   decrypt
            #   check local_md5
            # write on disk
            # TODO: implement
            pass
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
        elif self.type == _Task.LOCAL_MOVE:
            pass  # TODO: implement
        else:  # SYNC
            src_path = os.path.join(self.local_path, self.target)
            subtasks = []

            for name in os.listdir(src_path):
                abs_path = os.path.join(src_path, name)
                rel_path = os.path.relpath(name, self.local_path)
                if os.path.isdir(os.path.join(abs_path, name)):
                    _Task(_Task.SYNC, self.container, rel_path,
                          self.local_container)
                    # TODO: NEW SYNC TASK ?
                    f = None
                else:
                    # TODO: New XXX TASK ? comparison ?
                    f = None
                if f is not None:
                    subtasks.append(f)

            wait_all(subtasks)  # TODO: retry when result is None !
            # TODO: return value

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


@patch_dec
def added_remote_files(files):
    return Future.resolve(None)


@patch_dec
def changed_remote_files(files):
    return Future.resolve(None)


@patch_dec
def removed_remote_files(files):
    return Future.resolve(None)


@patch_dec
def added_local_files(container, local_container, filename):
    """Tells that a new file as been created and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the file created, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_ADD, container, filename, local_container)
    return task.start()


@patch_dec
def changed_local_files(container, local_container, filename):
    """Tells that a file has been modified and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the modified file, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_CHANGE, container, filename, local_container)
    return task.start()


@patch_dec
def removed_local_files(container, local_container, filename):
    """Tells that a file has been deleted and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the deleted file, relative to base_path.
    Returns:
        Future<boolean>: True if the task is successful; False if an error
            happened.
    """
    task = _Task(_Task.LOCAL_DELETION, container, filename, local_container)
    return task.start()


@patch_dec
def moved_local_files(container, local_container, src_filename, dest_filename):
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
    # TODO: to implement
    return Future.resolve(None)
