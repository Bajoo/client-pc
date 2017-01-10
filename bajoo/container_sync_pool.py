# -*- coding: utf-8 -*-

import datetime
from functools import partial
import heapq
import logging
import os
import threading

from . import filesync
from .api.sync import files_list_updater
from .app_status import AppStatus
from .common.i18n import _
from .common.strings import err2unicode
from .encryption.errors import PassphraseAbortError
from .filesync.added_local_files_task import AddedLocalFilesTask
from .filesync.filepath import is_path_allowed
from .filesync.moved_local_files_task import MovedLocalFilesTask
from .filesync.sync_scheduler import SyncScheduler
from .filesync.task_builder import TaskBuilder
from .file_watcher import FileWatcher
from .index.file_node import FileNode
from .index.hint_builder import HintBuilder
from .network.errors import HTTPEntityTooLargeError
from .promise import reduce_coroutine

_logger = logging.getLogger(__name__)


class ContainerSyncPool(object):
    """Group all containers and manages sync operations.

    It lists all LocalContainer instances, and start, pause, resume and stop
    the synchronisation for one or all containers.
    The class has a thread which read changes of containers, create tasks to
    sync them, and pass the tasks to the filesync module.

    Also, it updates container status and global status from the task's
    results.

    When a container is added to the pool, the sync of its files will begin
    (unless there has been an error in LocalContainer initialization).
    Local file changes and remote file changes will be detected and the
    index tree of the container will be updated via the HintBuilder.
    They will be "synced" later.

    Events are converted in "hint" as soon as possible, but tasks are generated
    and executed in order to not create them quicker than what the environment
    can handle (network and encryption are slow).

    """

    STATUS_STARTED = 'STARTED'
    STATUS_STOPPING = 'STOPPING'
    STATUS_STOPPED = 'STOPPED'

    QUOTA_TIMEOUT = 300.0

    def __init__(self, app_status, on_sync_error):
        """
        Args:
            app_status (AppStatus): application status object. It will be
                updated from container's sync progression.
            on_sync_error (callable): Called when an error occurs, with a str
                message as argument.
        """
        self._local_containers = {}
        self._on_sync_error = on_sync_error

        # Condition used for wake up the sync thread. It should be notified
        # after an external event (local or remote), or when the status is set
        # to STATUS_STOPPING
        self._condition = threading.Condition()
        # All following attributes must be protected by acquiring the
        # Condition.

        self._thread = None
        self._scheduler = SyncScheduler()

        self._ongoing_tasks = []

        # _failed_node is a heap (it must be manipulated by heapq functions)
        # Each tuple contains: (date of next try, nb of try already done,
        # index_tree, node)
        # type: List[Tuple[datetime.datetime, int, IndexTree, BaseNode]]
        self._failed_node = []

        self._app_status = app_status
        self._status = self.STATUS_STOPPED

    def start(self):
        with self._condition:
            if self._status == self.STATUS_STARTED:
                return
            if self._status == self.STATUS_STOPPING:
                # restart must be done only after the stop is done.
                self._condition.release()
                try:
                    self.stop(join=True)
                finally:
                    self._condition.acquire()

            for container, _updater, _watcher in self._local_containers:
                container.index_tree.set_tree_not_sync()
                self._scheduler.add_index_tree(container.index_tree)
                container.status = container.STATUS_STARTED
                container.error_msg = None
                _updater.start()
                _watcher.start()

            self._thread = threading.Thread(target=self._sync_thread,
                                            name="Sync Pool Thread")
            self._status = self.STATUS_STARTED
            self._thread.start()

    @reduce_coroutine()
    def add(self, local_container):
        """Add a container to sync.

        Either the container has been fetched at start of the dynamic container
        list, or it's a newly-added container.

        All containers are unlocked at add. When the unlock fails (ie: error
        network, no passphrase), the container is not added and the method
        raise an Exception.

        Args:
            local_container (LocalContainer)
        """
        container = local_container.container
        try:
            yield local_container.unlock()
        except Exception as err:
            msg = _('Container %s not started: %s') % (
                local_container.id, local_container.error_msg)
            if isinstance(err, PassphraseAbortError):
                _logger.info(msg)
            else:
                _logger.exception(msg)
            self._on_sync_error(msg)
            raise

        _logger.debug('Add container %s to sync list', container)

        last_remote_index = local_container.get_remote_index()

        updater = files_list_updater(
            container, local_container.path,
            partial(self._added_remote_files, local_container),
            partial(self._modified_remote_files, local_container),
            partial(self._removed_remote_files, local_container),
            None, last_remote_index)

        watcher = FileWatcher(local_container,
                              partial(self._added_local_file, local_container),
                              partial(self._modified_local_files,
                                      local_container),
                              partial(self._moved_local_files,
                                      local_container),
                              partial(self._removed_local_files,
                                      local_container))

        with self._condition:
            self._local_containers[container.id] = \
                (local_container, updater, watcher,)

            if self._status != self.STATUS_STARTED:
                local_container.status = local_container.STATUS_PAUSED
                return

            local_container.status = local_container.STATUS_STARTED
            if self._status == self.STATUS_STARTED:
                self._start_container(container.id)

    def _start_container(self, container_id):
        """Start the sync of a container present in the pool.

        Its status and error message are both reset.

        Args:
            container_id: ID of the container to start
        """
        lc, updater, watcher = self._local_containers[container_id]
        lc.index_tree.set_tree_not_sync()
        lc.status = lc.STATUS_STARTED
        lc.error_msg = None
        self._scheduler.add_index_tree(lc.index_tree)
        updater.start()
        watcher.start()
        self._condition.notify()

    def remove(self, local_container):
        """Remove a container and stop its sync operations.

        Note: if a container has been removed when bajoo was not running, this
        method will be called even if the container has never been added
        with ``self.add()``.

        Args:
            local_container (LocalContainer): container to remove
        """
        # TODO: remove node in error
        container_id = local_container.container.id
        with self._condition:
            if container_id in list(self._local_containers):
                self._stop_container(container_id)
                _logger.debug('Remove container %s from sync pool',
                              local_container)

    def _stop_container(self, container_id):
        """Stop the sync of a container.

        Args:
            container_id: ID of the container to remove.
        """
        (local_container, updater,
         watcher) = self._local_containers[container_id]

        self._scheduler.remove_index_tree(local_container.index_tree)
        updater.stop()
        watcher.stop()
        local_container.status = local_container.STATUS_STOPPED
        local_container.error_msg = None
        local_container.index_saver.stop()

        del self._local_containers[container_id]

    def pause(self):
        """Set all sync operations in pause."""
        _logger.debug('Pause sync')
        self.stop()
        with self._condition:
            self._app_status.value = AppStatus.SYNC_PAUSED

    def resume(self):
        """Resume sync operations if they are paused."""

        with self._condition:
            _logger.debug('Resume sync')
            self._app_status.value = AppStatus.SYNC_IN_PROGRESS
        self.start()

    def stop(self, join=False):
        """Stop the sync thread. All ongoing operations will be stopped."""
        with self._condition:
            if self._status == self.STATUS_STARTED:
                self._status = self.STATUS_STOPPING
                _logger.debug('Stop all containers ...')
                for local_container, __, __ in self._local_containers.values():
                    self._stop_container(local_container.container.id)
                _logger.info('Container Sync Pool stopping...')
                self._condition.notify()
            thread = self._thread
        if thread and join:
            thread.join()

    def _increment(self, task):
        with self._condition:
            self._ongoing_tasks.append(task)
            if self._app_status.value == AppStatus.SYNC_DONE:
                self._app_status.value = AppStatus.SYNC_IN_PROGRESS

    def _decrement(self, task):
        with self._condition:
            self._ongoing_tasks.remove(task)
            if self._app_status.value != AppStatus.SYNC_PAUSED:
                if not self._ongoing_tasks:
                    self._app_status.value = AppStatus.SYNC_DONE
                else:
                    self._app_status.value = AppStatus.SYNC_IN_PROGRESS

    def _apply_event_then_notify(func):
        def wrap(self, *args, **kwargs):
            with self._condition:
                if self._status != self.STATUS_STARTED:
                    return
                func(self, *args, **kwargs)
                self._condition.notify()
        return wrap

    @_apply_event_then_notify
    def _added_remote_files(self, container, files):
        for f in files:
            if is_path_allowed(f['name']):
                HintBuilder.apply_modified_event_from_path(
                    container.index_tree,
                    HintBuilder.SCOPE_REMOTE,
                    f['name'], f['hash'],
                    FileNode)
        _logger.log(5, 'Added %s remote files in %s', len(files), container)

    @_apply_event_then_notify
    def _removed_remote_files(self, container, files):
        for f in files:
            if is_path_allowed(f['name']):
                HintBuilder.apply_deleted_event_from_path(
                    container.index_tree,
                    HintBuilder.SCOPE_REMOTE,
                    f['name'])
        _logger.log(5, 'Removed %s remote files from %s', len(files),
                    container)

    @_apply_event_then_notify
    def _modified_remote_files(self, container, files):
        for f in files:
            if is_path_allowed(f['name']):
                HintBuilder.apply_modified_event_from_path(
                    container.index_tree,
                    HintBuilder.SCOPE_REMOTE,
                    f['name'], f['hash'],
                    FileNode)
        _logger.log(5, 'Modified %s remote files in %s', len(files), container)

    @_apply_event_then_notify
    def _added_local_file(self, container, file_path):
        filename = os.path.relpath(file_path, container.path)
        HintBuilder.apply_modified_event_from_path(
            container.index_tree,
            HintBuilder.SCOPE_LOCAL, filename,
            None, FileNode)
        _logger.log(5, 'Added local file "%s" in %s', filename, container)

    @_apply_event_then_notify
    def _removed_local_files(self, container, file_path):
        filename = os.path.relpath(file_path, container.path)
        HintBuilder.apply_deleted_event_from_path(container.index_tree,
                                                  HintBuilder.SCOPE_LOCAL,
                                                  filename)
        _logger.log(5, 'Removed local file "%s" from %s', filename, container)

    @_apply_event_then_notify
    def _modified_local_files(self, container, file_path):
        filename = os.path.relpath(file_path, container.path)
        HintBuilder.apply_modified_event_from_path(container.index_tree,
                                                   HintBuilder.SCOPE_LOCAL,
                                                   filename,
                                                   None, FileNode)
        _logger.log(5, 'Modified local file "%s" in %s', filename, container)

    @_apply_event_then_notify
    def _moved_local_files(self, container, src_path, dest_path):
        src_filename = os.path.relpath(src_path, container.path)
        dest_filename = os.path.relpath(dest_path, container.path)
        HintBuilder.apply_move_event_from_path(container.index_tree,
                                               HintBuilder.SCOPE_LOCAL,
                                               src_filename,
                                               dest_filename, FileNode)
        _logger.log(5, 'Moved local file from "%s" to "%s" in %s',
                    src_filename, dest_filename, container)

    def _is_failed_node_available(self):
        """Returns True when one (or more) failed node(s) can be retried."""
        return bool(self._failed_node and
                    self._failed_node[0][0] < datetime.datetime.now())

    def _get_next_node(self):
        """Get the next node to sync

        Returns:
            Tuple[int, IndexTree, baseNode]: nb of previous try, index_tree
                and node to sync. If none, returns (0, None, None).
        """
        # error nodes can have been removed from tree.
        while self._is_failed_node_available():
            __, nb_try, index_tree, node = heapq.heappop(
                self._failed_node)
            if not node.removed:
                return nb_try, index_tree, node

        if len(self._ongoing_tasks) < 30:
            index_tree, node = self._scheduler.get_node()
        else:
            index_tree, node = None, None
        return 0, index_tree, node

    def _sync_thread(self):
        with self._condition:
            while self._status == self.STATUS_STARTED:

                nb_try, index_tree, node = self._get_next_node()

                while node:
                    # Find the local container from the IndexTree.
                    # TODO: remove need of LocalContainer from task_factory.
                    local_container = next(
                        lc for (lc, _u, _w) in self._local_containers.values()
                        if lc.index_tree is index_tree)

                    with index_tree.lock:
                        self._create_task(local_container.container.id, node,
                                          index_tree, nb_try)

                    nb_try, index_tree, node = self._get_next_node()

                if self._failed_node:
                    time_to_wait = (self._failed_node[0][0] -
                                    datetime.datetime.now()).total_seconds()
                else:
                    time_to_wait = None  # wait until explicit notify()

                # wait for events which will produce new nodes to sync.
                self._condition.wait(time_to_wait)

            _logger.info('Stop sync thread')
            self._status = self.STATUS_STOPPED

    @reduce_coroutine(safeguard=True)
    def _create_task(self, container_id, node, index_tree, nb_try):
        """Create the task using the factory, then manages counter and errors.

        Args:
            container_id (str): id of the container.
            node (BaseNode): node to sync.
        """

        local_container, u, w = self._local_containers[container_id]

        if local_container.status in \
                (local_container.STATUS_STOPPED,
                 local_container.STATUS_PAUSED):
            _logger.debug('Local container is not running, abort task.')
            return
        task = TaskBuilder.build_from_node(local_container, node)
        if (local_container.status == local_container.STATUS_QUOTA_EXCEEDED and
                isinstance(task, (AddedLocalFilesTask, MovedLocalFilesTask))):
            _logger.debug('Quota exceeded, abort task.')
            return

        self._increment(task)
        TaskBuilder.acquire_from_task(node, task)

        try:
            # Note: due to async index_tree.lock is released during the yield.
            yield filesync.add_task(task)
        except Exception as err:
            self._on_task_failed(node, task, err, index_tree, nb_try)
        finally:
            with self._condition:
                self._condition.notify()
            self._decrement(task)

        local_container.index_saver.trigger_save()

    def _turn_delay_upload_off(self, local_container):
        with self._condition:
            if local_container.status != local_container.STATUS_QUOTA_EXCEEDED:
                _logger.debug('Fail to resume upload, local container' +
                              ' is not in quota exceeded status')
                return

            _logger.debug('Resume upload for container #: %s',
                          local_container.container.name)

            # Restart local container
            local_container.status = local_container.STATUS_STARTED
            local_container.error_msg = None
            local_container.index_tree.set_tree_not_sync()

    def delay_upload(self, local_container):
        with self._condition:
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

    def _on_task_failed(self, node, task, error, index_tree, nb_try):
        """A task has raised an error.

        Args:
            task (_Task): failed task
            error (Exception): the exception raised during the task execution.
        """
        nb_try2delta = {
            0: 30,  # 30s
            1: 5 * 60,  # 5m
            2: 3600,  # 1h
            3: 6 * 3600  # 6h
        }

        delay = nb_try2delta.get(nb_try, 24 * 36 * 3600)  # default: 1 day
        next_try = datetime.datetime.now() + datetime.timedelta(seconds=delay)
        nb_try += 1
        heapq.heappush(self._failed_node, (next_try, nb_try, index_tree, node))

        with index_tree.lock:
            node.error = error
            # A node in error is marked "sync" to prevent other sync attempt.
            node.sync = True

        # TODO: error messages should be grouped (over a period of 3-4 seconds)
        # to avoid spamming the user.
        # After 1st message, identical errors should not send new messages for
        # at least 1 minute.

        if isinstance(error, HTTPEntityTooLargeError):
            local_container = task.local_container
            self.delay_upload(local_container)
        else:
            target_string = ', '.join(task.target_list)
            self._on_sync_error(
                _('Error during sync of the file(s) "%(filename)s" '
                  'in the "%(name)s" container:\n%(error)s')
                % {'filename': target_string,
                   'name': task.container.name,
                   'error': err2unicode(error)})
