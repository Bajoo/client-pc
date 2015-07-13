# -*- coding: utf-8 -*-

import logging
import threading

from .api.sync import files_list_updater
from . import filesync

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

    def __init__(self):
        self._updaters = {}

        self._global_status = self.STATUS_UP_TO_DATE
        self._counter = 0
        self._counter_lock = threading.Lock()

    def add(self, local_container, container):
        """Add a container to sync.

        Either the container has been fetched at start of the dynamic container
        list, or it's a newly-added container.

        Args:
            local_container (LocalContainer)
            container (api.Container)
        """
        _logger.debug('Add container %s to sync list' % container)
        # TODO: give it the last known list.
        updater = files_list_updater(container, self._added_remote_file,
                                     self._modified_remote_files,
                                     self._removed_remote_files)
        self._updaters[container.id] = updater
        updater.start()

        # TODO: start updater for local files !

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
        if updater:
            updater.stop()
            del self._updaters[local_container.id]
            # TODO: stop current operations ...

    def pause(self):
        """Set all sync operations in pause."""
        _logger.debug('Pause sync')
        for u in self._updaters:
            u.stop()
            # TODO: stop current operations ...
        with self._counter_lock:
            self._global_status = self.STATUS_PAUSE

    def resume(self):
        """Resume sync operations if they are paused."""
        _logger.debug('Resume sync')
        for u in self._updaters:
            u.start()
        with self._counter_lock:
            if self._counter == 0:
                self._global_status = self.STATUS_UP_TO_DATE
            else:
                self._global_status = self.STATUS_SYNCING

    def _increment(self, _arg=None):
        with self._counter_lock:
            self._counter += 1
            if self._global_status != self.STATUS_PAUSE:
                self._global_status = self.STATUS_SYNCING

    def _decrement(self, _arg=None):
        with self._counter_lock:
            self._counter -= 1
            if self._global_status != self.STATUS_PAUSE:
                if self._counter == 0:
                    self._global_status = self.STATUS_UP_TO_DATE
                else:
                    self._global_status = self.STATUS_SYNCING

    def _added_remote_file(self, files):
        print('Added (remote): %s' % files)
        self._increment()
        filesync.added_remote_files(files).then(self._decrement)

    def _removed_remote_files(self, files):
        print('Removed (remote): %s' % files)
        self._increment()
        filesync.removed_remote_files(files).then(self._decrement)

    def _modified_remote_files(self, files):
        print('Modified (remote): %s' % files)
        self._increment()
        filesync.changed_remote_files(files).then(self._decrement)
