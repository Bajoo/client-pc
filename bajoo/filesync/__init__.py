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

The promise returns a list of failed tasks. If the operation is successful,
the list will be empty. If the task is a simple task and fails, the list will
contains the task itself.
If the task is more complex, and involves many subtasks, the list contains each
of the failed subtasks.
The failed tasks should be executed again latter.
"""

from .added_local_files_task import AddedLocalFilesTask
from .added_remote_files_task import AddedRemoteFilesTask
from .moved_local_files_task import MovedLocalFilesTask
from .removed_remote_files_task import RemovedRemoteFilesTask
from .removed_local_files_task import RemovedLocalFilesTask
from .sync_task import SyncTask
from .task_consumer import add_task


def added_remote_files(container, local_container, filename):
    task = AddedRemoteFilesTask(container, (filename,), local_container)
    return add_task(task)


def changed_remote_files(container, local_container, filename):
    task = AddedRemoteFilesTask(container, (filename,), local_container)
    return add_task(task)


def removed_remote_files(container, local_container, filename):
    task = RemovedRemoteFilesTask(container, (filename,), local_container)
    return add_task(task)


def added_local_files(container, local_container, filename):
    """Tells that a new file as been created and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the file created, relative to base_path.
    Returns:
        Promise<list of _Task>: List of failed tasks. Empty list if no error.
    """
    task = AddedLocalFilesTask(container, (filename,), local_container,
                               create_mode=True)
    return add_task(task)


def changed_local_files(container, local_container, filename):
    """Tells that a file has been modified and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the modified file, relative to base_path.
    Returns:
        Promise<list of _Task>: List of failed tasks. Empty list if no error.
    """
    task = AddedLocalFilesTask(container, (filename,), local_container,
                               create_mode=False)
    return add_task(task)


def removed_local_files(container, local_container, filename):
    """Tells that a file has been deleted and must be synced.

    Args:
        container (Container)
        local_container (LocalContainer)
        filename (str): filename of the deleted file, relative to base_path.
    Returns:
        Promise<list of _Task>: List of failed tasks. Empty list if no error.
    """
    task = RemovedLocalFilesTask(container, (filename,), local_container)
    return add_task(task)


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
        Promise<list of _Task>: List of failed tasks. Empty list if no error.
    """

    task = MovedLocalFilesTask(container, (src_filename, dest_filename,),
                               local_container)
    return add_task(task)


def sync_folder(container, local_container, folder_path):
    """Sync a local folder

    Args:
        container (Container)
        local_container (LocalContainer)
        folder_path (str): path of the directory, relative to base_path.
    Returns:
        Promise<list of _Task>: List of failed tasks. Empty list if no error.
    """
    task = SyncTask(container, (folder_path,), local_container)
    return add_task(task)
