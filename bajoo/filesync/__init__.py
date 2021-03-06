# -*- coding: utf-8 -*-

"""Synchronize files between local filesystem and remote Bajoo servers.

The module contains a thread dedicated to comparison and verification of files.
It executes a list of "tasks" (each task type is represented by a class)
created by the TaskBuilder.

When calling `add_task()`, a task is added to the queue, and will performs the
needed operation to keep local and remote folders synced.

The tasks send network requests, ask for encryption, and so will often wait
asynchronous operations. Many tasks will be executed in parallel.

Each task takes in parameters the local container. It will be used to retrieve
the hashes corresponding to the concerned files.
When done, it generates a dict containing the new values for theses hashes. If
the dict is empty (or if some items are missing), the original hash values are
removed. When an error occurs, the new index fragment is not generated. In this
case, the original hash values are not modified.

The promise returns None when the task target has been synced. If an error
occurs, the Promise fails with this error.
The failed tasks should be executed again latter (an error can be temporary).
Anyway, the node acquired by the task is released before the Promise fail or
succeed.
"""

from .task_consumer import add_task
from .task_builder import TaskBuilder

__all__ = [
    add_task,
    TaskBuilder
]
