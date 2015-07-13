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

When calling one of theses methods, a task is added to performs the needed
operation to keep local and remote folders synced.
If the tasks need to works on many files (eg: a task on a folder containing
subfolders), it can be executed partially and "splitted" in many small tasks.

The tasks send network requests, ask for encryption, and so will often wait
asynchronous operations. Many tasks will be executed in parallel.
"""

from ..common.future import Future


from concurrent.futures import ThreadPoolExecutor

_thread_pool = ThreadPoolExecutor(max_workers=1)


def added_remote_files(files):
    return Future.resolve(None)


def changed_remote_files(files):
    return Future.resolve(None)


def removed_remote_files(files):
    return Future.resolve(None)


def added_local_files():
    return Future.resolve(None)


def changed_local_files():
    return Future.resolve(None)


def removed_local_files():
    return Future.resolve(None)
