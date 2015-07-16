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
"""

from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
import logging
import os

from ..common.future import Future, patch_dec

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

    def __init__(self, type, container, target, local_path, local_md5=None,
                 remote_md5=None):
        self.type = type
        self.container = container
        self.target = target
        self.local_path = local_path
        self.local_md5 = local_md5
        self.remote_md5 = remote_md5

    def __repr__(self):
        return ('<Task %s %s local_path=%s>' %
                (self.type.upper(), self.target, self.local_path))

    def execute(self):
        try:
            return self._apply_task()
        except:
            # TODO: These errors should be reported to the user, and the
            # concerned files should be excluded of the sync for a period of
            # 24h if they keep failing.
            _logger.exception('Exception on filesync task:')

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
                md5 = self._compute_md5_hash(file_content)
                if self.remote_md5 and md5 == self.local_md5:  # Nothing to do
                    _logger.debug('local md5 hash has not changed. '
                                  'No need to upload.')
                    file_content.close()
                    return {self.target: (self.local_md5, self.remote_md5)}
                file_content.seek(0)
            except (IOError, OSError) as err:
                if err.errno == errno.ENOENT and self.type == _Task.LOCAL_ADD:
                    # The file is gone before we've done anything.
                    return {}
                if file_content:
                    file_content.close()
                raise
            except:
                if file_content:
                    file_content.close()
                raise

            self.container.upload(self.target, file_content)
            # TODO: check upload error
            # TODO: return value
        elif self.type == _Task.LOCAL_DELETION:
            # Delete remote file
            self.container.remove_file(self.target)
            # TODO: check error.
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
                    _logger.debug('The file to delete is not present on the'
                                  'disk: nothing to do.')
                    raise
            return {}
        elif self.type == _Task.LOCAL_MOVE:
            pass  # TODO: implement
        else:  # SYNC
            # TODO: sync ...
            pass

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
def added_local_files(container, base_path, filename):
    """Tells that a new file as been created and must be synced.

    Args:
        container (Container)
        base_path (str): path of the container's folder.
        filename (str): filename of the file created, relative to base_path.
    Returns:
        Future<dict>: Part of index of the corresponding files, of the form
            {filename: (local_hash, remote_hash)}.
    """
    task = _Task(_Task.LOCAL_ADD, container, filename, base_path)
    return _thread_pool.submit(task.execute)


@patch_dec
def changed_local_files(container, base_path, filename, local_md5, remote_md5):
    """Tells that a file has been modified and must be synced.

    Args:
        container (Container)
        base_path (str): path of the container's folder.
        filename (str): filename of the modified file, relative to base_path.
        local_md5 (str): last known md5 hash of the (local) file.
        remote_md5 (str): last known md5 hash of the distant file.
    Returns:
        Future<dict>: Part of index of the corresponding files, of the form
            {filename: (local_hash, remote_hash)}.
    """
    task = _Task(_Task.LOCAL_CHANGE, container, filename, base_path)
    return _thread_pool.submit(task.execute)


@patch_dec
def removed_local_files(container, base_path, filename, local_md5, remote_md5):
    """Tells that a file has been deleted and must be synced.

    Args:
        container (Container)
        base_path (str): path of the container's folder.
        filename (str): filename of the deleted file, relative to base_path.
        local_md5 (str): last known md5 hash of the (local) file.
        remote_md5 (str): last known md5 hash of the distant file.
    Returns:
        Future<dict>: Part of index of the corresponding files, of the form
            {filename: (local_hash, remote_hash)}.
    """
    task = _Task(_Task.LOCAL_DELETION, container, filename, base_path,
                 local_md5=local_md5, remote_md5=remote_md5)
    return _thread_pool.submit(task.execute)


@patch_dec
def moved_local_files(container, base_path, src_filename, dest_filename,
                      local_src_md5, local_dest_md5,
                      remote_src_md5, remote_dest_md5):
    """Tells that a file has been moved, and must be synced.

    Args:
        container (Container)
        base_path (str): path of the container's folder.
        src_filename (str): source filename of the moved file, relative to
            base_path.
        dest_filename (str): destination filename of the movedfile, relative to
            base_path.
        local_src_md5 (str): last known md5 hash of the local source file.
        remote_src_md5 (str): last known md5 hash of the distant source file.
        local_dest_md5 (str): last known md5 hash of the local destination
            file who have been replaced.
        remote_dest_md5 (str): last known md5 hash of the distant destination
            file who have been replaced.
    Returns:
        Future<dict>: Part of index of the corresponding files, of the form
            {filename: (local_hash, remote_hash)}.
    """
    # TODO: to implement
    return Future.resolve(None)
