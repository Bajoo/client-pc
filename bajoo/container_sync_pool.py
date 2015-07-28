# -*- coding: utf-8 -*-

from functools import partial
import logging
import os
import threading

from .api.sync import files_list_updater
from . import filesync
from .file_watcher import FileWatcher

_logger = logging.getLogger(__name__)


class ContainerSyncPool(object):
    """Group all containers and manages sync operations.

    When a container is added to the pool, the sync of its files will begin
    (unless there has been an error in LocalContainer initialization).
    Local file changes and remote file changes will be detected and applied as
    soon as possible by adding tasks to the bajoo.filesync module.

    pause() and resume() allow to stop (and restart) sync for all containers
    at once.
    """

    STATUS_SYNCING = 1
    STATUS_UP_TO_DATE = 2
    STATUS_PAUSE = 3

    def __init__(self, on_state_change, on_sync_error):
        """
        Args:
            on_state_change (callable): called when the global state change.
        """
        self._containers = {}
        self._local_containers = {}
        self._updaters = {}
        self._local_watchers = {}

        self._on_state_change = on_state_change
        self._on_sync_error = on_sync_error

        self._global_status = self.STATUS_UP_TO_DATE
        self._counter = 0
        self._status_lock = threading.Lock()

    def add(self, local_container, container):
        """Add a container to sync.

        Either the container has been fetched at start of the dynamic container
        list, or it's a newly-added container.

        Args:
            local_container (LocalContainer)
            container (api.Container)
        """
        _logger.debug('Add container %s to sync list' % container)

        self._containers[container.id] = container
        self._local_containers[container.id] = local_container

        last_remote_index = local_container.get_remote_index()

        updater = files_list_updater(
            container,
            partial(self._added_remote_file, container.id),
            partial(self._modified_remote_files, container.id),
            partial(self._removed_remote_files, container.id),
            None, last_remote_index)

        self._updaters[container.id] = updater
        updater.start()

        watcher = FileWatcher(local_container,
                              partial(self._added_local_file, container.id),
                              partial(self._modified_local_files,
                                      container.id),
                              partial(self._moved_local_files, container.id),
                              partial(self._removed_local_files, container.id))
        self._local_watchers[container.id] = watcher
        watcher.start()

        self._create_task(filesync.sync_folder, container.id, '.')

    def remove(self, local_container):
        """Remove a container and stop its sync operations.

        Note: if a container has been removed when bajoo was not running, this
        method will be called even if the container has never been added
        with ``self.add()``.

        Args:
            local_container (LocalContainer)
        """
        _logger.debug('Remove container %s from sync list' % local_container)
        updater = self._updaters.get(local_container.id)
        watcher = self._local_watchers.get(local_container.id)
        if updater:
            updater.stop()
            del self._updaters[local_container.id]
            # TODO: stop current operations ...
        if watcher:
            watcher.stop()

    def pause(self):
        """Set all sync operations in pause."""
        _logger.debug('Pause sync')
        for u in self._updaters:
            u.stop()
            # TODO: stop current operations ...
        for w in self._local_watchers:
            w.stop()
        with self._status_lock:
            self._global_status = self.STATUS_PAUSE
            self._on_state_change(self._global_status)

    def resume(self):
        """Resume sync operations if they are paused."""
        _logger.debug('Resume sync')
        for u in self._updaters:
            u.start()
        for w in self._local_watchers:
            w.start()
        with self._status_lock:
            if self._counter == 0:
                self._global_status = self.STATUS_UP_TO_DATE
            else:
                self._global_status = self.STATUS_SYNCING
            self._on_state_change(self._global_status)

        for container in self._containers:
            self._create_task(filesync.sync_folder, container.id, '.')

    def _increment(self, _arg=None):
        with self._status_lock:
            self._counter += 1
            if self._global_status == self.STATUS_UP_TO_DATE:
                self._global_status = self.STATUS_SYNCING
                self._on_state_change(self._global_status)

    def _decrement(self, _arg=None):
        with self._status_lock:
            self._counter -= 1
            if self._global_status != self.STATUS_PAUSE:
                if self._counter == 0:
                    if self._global_status != self.STATUS_UP_TO_DATE:
                        self._global_status = self.STATUS_UP_TO_DATE
                        self._on_state_change(self._global_status)
                elif self._global_status != self.STATUS_SYNCING:
                    self._global_status = self.STATUS_SYNCING
                    self._on_state_change(self._global_status)

    def _added_remote_file(self, container_id, files):
        print('Added (remote): %s' % files)
        for f in files:
            self._create_task(filesync.added_remote_files, container_id,
                              f['name'])

    def _removed_remote_files(self, container_id, files):
        print('Removed (remote): %s' % files)
        for f in files:
            self._create_task(filesync.removed_remote_files, container_id,
                              f['name'])

    def _modified_remote_files(self, container_id, files):
        print('Modified (remote): %s' % files)
        for f in files:
            self._create_task(filesync.changed_remote_files, container_id,
                              f['name'])

    def _added_local_file(self, container_id, file_path):
        print('Added (local): %s for %s' % (file_path, container_id))
        local_container = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.path)

        self._create_task(filesync.added_local_files, container_id, filename)

    def _removed_local_files(self, container_id, file_path):
        print('Removed (local): %s for %s' % (file_path, container_id))
        local_container = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.path)

        self._create_task(filesync.removed_local_files, container_id, filename)

    def _modified_local_files(self, container_id, file_path):
        print('Modified (local): %s for %s' % (file_path, container_id))
        local_container = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.path)

        self._create_task(filesync.changed_local_files, container_id, filename)

    def _moved_local_files(self, container_id, src_path, dest_path):
        print('Moved (local): %s -> %s' % (src_path, dest_path))
        local_container = self._local_containers[container_id]
        src_filename = os.path.relpath(src_path, local_container.path)
        dest_filename = os.path.relpath(dest_path, local_container.path)

        self._create_task(filesync.moved_local_files, container_id,
                          src_filename, dest_filename)

    def _create_task(self, task_factory, container_id, *args):
        """Create the task using the factory, then manages counter and errors.

        Args:
            task_factory (callable): function who generates a new task. it
                must accept a container and a local_container as its 1rst and
                2nd arguments, and a callback as named argument
                'display_error_cb'.
            container_id (str): id of the container.
            *args (...): supplementary args passed to the
                task_factory.
        """
        container = self._containers[container_id]
        local_container = self._local_containers[container_id]

        self._increment()
        f = task_factory(container, local_container, *args,
                         display_error_cb=self._on_sync_error)
        if f:
            f.then(self._decrement)
        else:  # The task has been "merged" with another.
            self._decrement()
