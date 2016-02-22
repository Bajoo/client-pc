# -*- coding: utf-8 -*-

from functools import partial
import logging
import os
import threading

from .api.sync import files_list_updater
from . import filesync
from .file_watcher import FileWatcher
from .filesync.filepath import is_path_allowed
from .network.errors import HTTPEntityTooLargeError
from .encryption.errors import PassphraseAbortError
from .common.i18n import _


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

    QUOTA_TIMEOUT = 300.0

    def __init__(self, on_state_change, on_sync_error):
        """
        Args:
            on_state_change (callable): called when the global state change.
        """
        self._local_containers = {}
        self._on_state_change = on_state_change
        self._on_sync_error = on_sync_error

        self._global_status = self.STATUS_UP_TO_DATE
        self._counter = 0
        self._passphrase_needed = False

        self._inner_lock = threading.RLock()

    def add(self, local_container):
        """Add a container to sync.

        Either the container has been fetched at start of the dynamic container
        list, or it's a newly-added container.

        Args:
            local_container (LocalContainer)
        """
        container = local_container.container
        _logger.debug('Add container %s to sync list' % container)

        last_remote_index = local_container.get_remote_index()

        updater = files_list_updater(
            container, local_container.model.path,
            partial(self._added_remote_file, container.id),
            partial(self._modified_remote_files, container.id),
            partial(self._removed_remote_files, container.id),
            None, last_remote_index)

        watcher = FileWatcher(local_container.model,
                              partial(self._added_local_file, container.id),
                              partial(self._modified_local_files,
                                      container.id),
                              partial(self._moved_local_files, container.id),
                              partial(self._removed_local_files, container.id))

        with self._inner_lock:
            self._local_containers[container.id] = \
                (local_container, updater, watcher,)

            if self._global_status == ContainerSyncPool.STATUS_PAUSE:
                local_container.status = local_container.STATUS_PAUSED
                return

            if self._passphrase_needed and container.is_encrypted:
                local_container.status = local_container.STATUS_WAIT_PASSPHRASE
                local_container.error_msg = _(
                    'No passphrase set.  Syncing is disabled')
                return

            local_container.status = local_container.STATUS_STARTED
            updater.start()
            watcher.start()
            self._create_task(filesync.sync_folder, container.id, u'.')

    def remove(self, container_id):
        """Remove a container and stop its sync operations.

        Note: if a container has been removed when bajoo was not running, this
        method will be called even if the container has never been added
        with ``self.add()``.

        Args:
            local_container (LocalContainer)
        """

        with self._inner_lock:
            if container_id in list(self._local_containers):
                lc, updater, watcher = self._local_containers[container_id]

                lc.status = lc.STATUS_STOPPED
                updater.stop()
                watcher.stop()
                lc.error_msg = None
                lc.index_saver.stop()

                del self._local_containers[container_id]

                _logger.debug('Remove container %s from sync list' % lc)

                return lc

            return None

    def _pause_if_need_the_passphrase(self):
        with self._inner_lock:
            if self._passphrase_needed:
                _logger.debug('Local containers are already waiting for' +
                              ' the passphrase')
                return

            self._passphrase_needed = True

            self._on_sync_error(_('No passphrase set.  Cyphered containers' +
                                  ' will be paused'))

            if self._global_status == ContainerSyncPool.STATUS_PAUSE:
                return

            for lc, updater, watcher in self._local_containers.values():
                if lc.status == lc.STATUS_PAUSED:
                    continue

                if not lc.container.is_encrypted:
                    continue

                lc.status = lc.STATUS_WAIT_PASSPHRASE
                updater.stop()
                watcher.stop()
                lc.error_msg = _('No passphrase set.  Syncing is disabled')

    def resume_if_wait_for_the_passphrase(self):
        with self._inner_lock:
            if not self._passphrase_needed:
                _logger.debug('Local containers are already unpaused')
                return

            self._passphrase_needed = False

            if self._global_status == ContainerSyncPool.STATUS_PAUSE:
                return

            for lc, updater, watcher in self._local_containers.values():
                if lc.status != lc.STATUS_WAIT_PASSPHRASE:
                    continue

                lc.status = lc.STATUS_STARTED
                lc.error_msg = None
                updater.start()
                watcher.start()
                self._create_task(filesync.sync_folder, lc.model.id, u'.')

    def pause(self):
        """Set all sync operations in pause."""
        with self._inner_lock:
            _logger.debug('Pause sync')
            for lc, updater, watcher in self._local_containers.values():
                lc.status = lc.STATUS_PAUSED
                updater.stop()
                watcher.stop()
                lc.error_msg = None

                self._global_status = self.STATUS_PAUSE
                self._on_state_change(self._global_status)

    def resume(self):
        """Resume sync operations if they are paused."""

        with self._inner_lock:
            _logger.debug('Resume sync')

            if self._counter == 0:
                self._global_status = self.STATUS_UP_TO_DATE
            else:
                self._global_status = self.STATUS_SYNCING
            self._on_state_change(self._global_status)

            for lc, updater, watcher in self._local_containers.values():
                if self._passphrase_needed and lc.container.is_encrypted:
                    lc.status = lc.STATUS_WAIT_PASSPHRASE
                    lc.error_msg = _('No passphrase set.  Syncing is disabled')
                else:
                    lc.status = lc.STATUS_STARTED
                    lc.error_msg = None
                    updater.start()
                    watcher.start()
                    self._create_task(filesync.sync_folder, lc.model.id, u'.')

    def stop(self):
        for container_id in list(self._local_containers):
            self.remove(container_id)

    def _increment(self, _arg=None):
        with self._inner_lock:
            self._counter += 1
            if self._global_status == self.STATUS_UP_TO_DATE:
                self._global_status = self.STATUS_SYNCING
                self._on_state_change(self._global_status)

    def _decrement(self, _arg=None):
        with self._inner_lock:
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
        _logger.info('Added (remote): %s' % files)
        for f in files:
            if is_path_allowed(f['name']):
                self._create_task(filesync.added_remote_files, container_id,
                                  f['name'])

    def _removed_remote_files(self, container_id, files):
        _logger.info('Removed (remote): %s' % files)
        for f in files:
            if is_path_allowed(f['name']):
                self._create_task(filesync.removed_remote_files, container_id,
                                  f['name'])

    def _modified_remote_files(self, container_id, files):
        _logger.info('Modified (remote): %s' % files)
        for f in files:
            if is_path_allowed(f['name']):
                self._create_task(filesync.changed_remote_files, container_id,
                                  f['name'])

    def _added_local_file(self, container_id, file_path):
        _logger.info('Added (local): %s for %s' % (file_path, container_id))
        local_container, u, w = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.model.path)

        self._create_task(filesync.added_local_files, container_id, filename)

    def _removed_local_files(self, container_id, file_path):
        _logger.info('Removed (local): %s for %s' % (file_path, container_id))
        local_container, u, w = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.model.path)

        self._create_task(filesync.removed_local_files, container_id, filename)

    def _modified_local_files(self, container_id, file_path):
        _logger.info('Modified (local): %s for %s' % (file_path, container_id))
        local_container, u, w = self._local_containers[container_id]
        filename = os.path.relpath(file_path, local_container.model.path)

        self._create_task(filesync.changed_local_files, container_id, filename)

    def _moved_local_files(self, container_id, src_path, dest_path):
        _logger.info('Moved (local): %s -> %s' % (src_path, dest_path))
        local_container, u, w = self._local_containers[container_id]
        src_filename = os.path.relpath(src_path, local_container.model.path)
        dest_filename = os.path.relpath(dest_path, local_container.model.path)

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

        local_container, u, w = self._local_containers[container_id]

        if local_container.status in \
            (local_container.STATUS_STOPPED,
             local_container.STATUS_PAUSED,
             local_container.STATUS_WAIT_PASSPHRASE,):
            _logger.debug('Local container is not running, abort task.')
            return

        elif local_container.status == \
            local_container.STATUS_QUOTA_EXCEEDED and \
            (task_factory is filesync.added_local_files or
             task_factory is filesync.moved_local_files):
            _logger.debug('Quota exceeded, abort task.')
            return

        container = local_container.container

        self._increment()
        f = task_factory(container, local_container, *args,
                         display_error_cb=self._on_sync_error)

        if f:
            f.then(self._on_task_success, self._on_task_failed).safeguard()
        else:  # The task has been "merged" with another.
            self._decrement()

    def _turn_delay_upload_off(self, local_container):
        with self._inner_lock:
            if local_container.status != local_container.STATUS_QUOTA_EXCEEDED:
                _logger.debug('Fail to resume upload, local container' +
                              ' is not in quota exceeded status')
                return

            _logger.debug('Resume upload for container #: %s',
                          local_container.container.name)

            # Restart local container
            local_container.status = local_container.STATUS_STARTED
            local_container.error_msg = None
            self._create_task(filesync.sync_folder,
                              local_container.container.id, u'.')

    def delay_upload(self, local_container):
        with self._inner_lock:
            if local_container.status == local_container.STATUS_QUOTA_EXCEEDED:
                _logger.debug('Quota limit has already been detected')
                return

            _logger.debug('Delay upload for container #: %s',
                          local_container.container.name)

            self._on_sync_error(_("Quota limit reached"))

            local_container.status = local_container.STATUS_QUOTA_EXCEEDED
            local_container.error_msg = _(
                'Your quota has exceeded.' +
                ' All upload operations are delayed in the next 5 minutes.')
            threading.Timer(self.QUOTA_TIMEOUT, self._turn_delay_upload_off,
                            [local_container]) \
                .start()

    def _on_task_success(self, _arg=None):
        """This method can be called in three different cases:
        A) the task and its subtasks are successful
        B) the task is successful but a subtask failed
        C) the task failed but it is not a "container related" error

        So if the root task is in the list, the kind or error to manage here is
        normal or local behaviour.
        But if there is a subtask in the list, it could be a
        "container related" error or not...

        In cas B) or C), the argument _arg will be populated with the
        failing tasks

        Args:
            _arg(list(_Task)): None or the list of failing taks

        """

        # TODO: If the task factory returns a list of failed tasks, the tasks
        # should be retried and the concerned files should be excluded of
        # the sync for a period of 24h if they keep failing.

        if _arg is not None:
            upload_limit_reached = False
            passphrase_not_set = False

            for task in _arg:
                if isinstance(task.error, HTTPEntityTooLargeError):
                    upload_limit_reached = True

                if isinstance(task.error, PassphraseAbortError):
                    passphrase_not_set = True

                if hasattr(task.error, 'container_id'):
                    self._manage_container_error(task.error)

            if upload_limit_reached:
                local_container = task.local_container
                self.delay_upload(local_container)

            if passphrase_not_set:
                self._pause_if_need_the_passphrase()

        self._decrement()

    def _on_task_failed(self, error):
        """A task has raised a "container related" error.

        If this happens, it means the container itself is in an error state:
        the container key is unusable. It can be either a network error or an
        encryption error (bad .key, missing or wrong passphrase, ...).

        Args:
            error (Exception): the exception raised during the task execution

        """

        if hasattr(error, 'container_id'):
            self._manage_container_error(error)

        self._decrement()

    def _manage_container_error(self, error):
        # TODO only a failed download of the encryption key
        # will trigger this statement, is it normal ?
        # should it manage other container error ?

        # TODO and once the local container is in error state
        # what is it supposed to do ?

        local_container = self.remove(error.container_id)
        local_container.status = local_container.STATUS_ERROR
        local_container.error_msg = str(error)
