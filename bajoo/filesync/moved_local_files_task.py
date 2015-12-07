#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: optimization: move the file server-side.

import itertools
import logging
import os

from .abstract_task import _Task
from .added_local_files_task import PushTaskMixin
from ..network.errors import HTTPNotFoundError
from ..promise import Promise
from .removed_local_files_task import RemovedTaskMixin
from .task_consumer import add_task

TASK_NAME = 'local_move'

_logger = logging.getLogger(__name__)

ACTION_EXIT = 0
ACTION_CHECK_LOCAL_SRC_FILE = 1
ACTION_CHECK_LOCAL_DEST_FILE = 2
ACTION_CHECK_REMOTE_SRC_FILE = 3
ACTION_RISK_OF_CONFLICT_REMOTE_SRC_FILE = 4
ACTION_TRY_TO_OVERWRITE_LOCAL_DEST = 5
ACTION_CHECK_REMOTE_DEST_FILE = 6
ACTION_UPLOAD_DEST_FILE = 7
ACTION_RISK_OF_CONFLICT_REMOTE_DEST_FILE = 8
ACTION_REMOVE_REMOTE_SRC_FILE = 9


class MovedStateMachineStatus(object):

    def __init__(self, task, source_target, destination_target):
        self.task = task
        self.source_target = source_target
        self.destination_target = destination_target
        self.task_list = None
        self.files_status = None
        self.remote_src_file_content = None
        self.remote_src_file_cyphered_md5 = None
        self.current_local_dest_md5 = None
        self.skip_remote_source_remove = False

    def add_task(self, task):
        if self.task_list is None:
            self.task_list = []

        self.task_list.append(add_task(task, priority=True))

    def get_current_local_dest_md5(self):
        if self.current_local_dest_md5 is not None:
            return self.current_local_dest_md5

        dest_path = os.path.join(self.task.local_path,
                                 self.destination_target.rel_path)

        with open(dest_path, 'rb') as file_content:
            self.current_local_dest_md5 = self.task._compute_md5_hash(
                file_content)

        return self.current_local_dest_md5

    def set_file_status(self, rel_path, local_hash, remote_hash):
        if self.files_status is None:
            self.files_status = {}

        self.files_status[rel_path] = (local_hash, remote_hash,)


class MovedLocalFilesTask(_Task, PushTaskMixin, RemovedTaskMixin):

    def __init__(self, container, target, local_container,
                 display_error_cb, parent_path=None):

        _Task.__init__(self, container, target, local_container,
                       display_error_cb, parent_path, expected_target_count=2)

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)
        state = MovedStateMachineStatus(self, self.target_list[0],
                                        self.target_list[1])
        next_action = ACTION_CHECK_LOCAL_SRC_FILE

        while next_action != ACTION_EXIT:
            if next_action == ACTION_CHECK_LOCAL_SRC_FILE:
                next_action = self.check_local_source_file(state)

            elif next_action == ACTION_CHECK_LOCAL_DEST_FILE:
                next_action = self.check_local_dest_file_exists(state)

            elif next_action == ACTION_CHECK_REMOTE_SRC_FILE:
                if state.source_target.remote_md5 is None:
                    next_action = ACTION_RISK_OF_CONFLICT_REMOTE_SRC_FILE
                    continue

                try:
                    metadata = yield self.container.get_info_file(
                        state.source_target.rel_path)
                    remote_src_cyphered_md5 = metadata['hash']
                except HTTPNotFoundError:
                    state.skip_remote_source_remove = True
                    remote_src_cyphered_md5 = None

                next_action = self.check_remote_src_file(
                    state,
                    remote_src_cyphered_md5)

            elif next_action == ACTION_RISK_OF_CONFLICT_REMOTE_SRC_FILE:
                try:
                    result = yield self.container.download(
                        state.source_target.rel_path)
                    metadata, state.remote_src_file_content = result
                    state.remote_src_file_cyphered_md5 = metadata['hash']
                except HTTPNotFoundError:
                    state.skip_remote_source_remove = True
                    state.remote_src_file_content = None

                next_action = self.conflict_remote_src_file(state)

            elif next_action == ACTION_TRY_TO_OVERWRITE_LOCAL_DEST:
                next_action = self.try_to_overwrite_local_dest_file(state)

            elif next_action == ACTION_CHECK_REMOTE_DEST_FILE:
                if state.destination_target.remote_md5 is None:
                    next_action = ACTION_RISK_OF_CONFLICT_REMOTE_DEST_FILE
                    continue

                try:
                    metadata = yield self.container.get_info_file(
                        state.destination_target.rel_path)
                    remote_dest_cyphered_md5 = metadata['hash']
                except HTTPNotFoundError:
                    remote_dest_cyphered_md5 = None

                next_action = self.check_remote_dest_file(
                    state,
                    remote_dest_cyphered_md5)

            elif next_action == ACTION_RISK_OF_CONFLICT_REMOTE_DEST_FILE:
                try:
                    result = yield self.container.download(
                        state.destination_target.rel_path)
                    metadata, remote_dest_file = result
                    remote_dest_cyphered_md5 = metadata['hash']
                except HTTPNotFoundError:
                    remote_dest_file = None
                    remote_dest_cyphered_md5 = None

                next_action = self.conflict_remote_dest_file(
                    state,
                    remote_dest_file,
                    remote_dest_cyphered_md5)

            elif next_action == ACTION_UPLOAD_DEST_FILE:
                _logger.debug('upload destination file: \'%s\'' %
                              state.destination_target.rel_path)

                dest_path = os.path.join(self.local_path,
                                         state.destination_target.rel_path)

                with open(dest_path, 'rb') as file_content:
                    metadata = yield self.container.upload(
                        state.destination_target.rel_path,
                        file_content)

                current_local_dest_md5 = state.get_current_local_dest_md5()

                state.set_file_status(state.destination_target.rel_path,
                                      current_local_dest_md5,
                                      metadata['hash'])

                next_action = ACTION_REMOVE_REMOTE_SRC_FILE

            elif next_action == ACTION_REMOVE_REMOTE_SRC_FILE:
                if state.skip_remote_source_remove:
                    _logger.debug('Remote source file must be kept or does '
                                  'not exist. Do not try to remove it.')

                    next_action = ACTION_EXIT
                    continue

                _logger.debug('Try to remove remote source file')

                try:
                    yield self.container.remove_file(
                        state.source_target.rel_path)
                except HTTPNotFoundError:
                    pass

                next_action = ACTION_EXIT
            else:
                _logger.error('Unknown next_action <%s>' % str(next_action))
                next_action = ACTION_EXIT

        if state.task_list is not None and len(state.task_list) > 0:
            self._release_index(result=state.files_status)
            state.files_status = None

            results = yield Promise.all(state.task_list)
            failed_tasks = itertools.chain(*filter(None, results))
            failed_tasks = list(failed_tasks)

            if failed_tasks:
                self._task_errors = failed_tasks

        yield state.files_status
        return

    def check_local_source_file(self, state):
        src_path = os.path.join(self.local_path, state.source_target.rel_path)
        if not os.path.exists(src_path):
            return ACTION_CHECK_LOCAL_DEST_FILE

        _logger.debug('Local source file exists. Abort!')

        new_file = state.source_target.local_md5 is None
        state.add_task(self._create_push_task(state.source_target.rel_path,
                                              new_file))

        dest_path = os.path.join(self.local_path,
                                 state.destination_target.rel_path)
        if os.path.exists(dest_path):
            new_file = state.destination_target.local_md5 is None
            state.add_task(self._create_push_task(
                state.destination_target.rel_path,
                new_file))

        else:
            state.add_task(self._create_a_remove_task(
                state.destination_target.rel_path))

        return ACTION_EXIT

    def check_local_dest_file_exists(self, state):
        dest_path = os.path.join(self.local_path,
                                 state.destination_target.rel_path)
        if os.path.exists(dest_path):
            return ACTION_CHECK_REMOTE_SRC_FILE

        _logger.debug('Local destination file does not exist. Abort!')

        state.add_task(self._create_a_remove_task(
            state.destination_target.rel_path))

        # at this point, local_src_file has been localy deleted
        state.add_task(self._create_a_remove_task(
            state.source_target.rel_path))

        return ACTION_EXIT

    def check_remote_src_file(self, state, remote_hash):
        if remote_hash is None or \
           state.source_target.remote_md5 == remote_hash:
            return ACTION_CHECK_REMOTE_DEST_FILE

        _logger.debug('Don\t know if remote source is the same or if remote'
                      ' hash is different, download it and check.')

        return ACTION_RISK_OF_CONFLICT_REMOTE_SRC_FILE

    def conflict_remote_src_file(self, state):
        if state.remote_src_file_content is None:
            return ACTION_CHECK_REMOTE_DEST_FILE

        try:
            md5 = self._compute_md5_hash(state.remote_src_file_content)
            state.remote_src_file_content.seek(0)
        except:
            state.remote_src_file_content.close()
            raise

        if state.source_target.local_md5 == md5:
            state.remote_src_file_content.close()
            return ACTION_CHECK_REMOTE_DEST_FILE
        else:
            _logger.debug('Conflict with the remote source file!')

            return ACTION_TRY_TO_OVERWRITE_LOCAL_DEST

    def try_to_overwrite_local_dest_file(self, state):
        if state.remote_src_file_content is None:
            _logger.debug('No conflict anymore.')
            return ACTION_CHECK_REMOTE_DEST_FILE

        current_local_dest_md5 = state.get_current_local_dest_md5()

        if state.source_target.local_md5 == current_local_dest_md5:
            _logger.debug('Move remote source file to the new destination.')

            state.current_local_dest_md5 = self._write_downloaded_file(
                state.remote_src_file_content,
                state.destination_target)
        else:
            _logger.debug('Conflict with the file at the new destination!  '
                          'Recreate at source.  ')

            local_src_md5 = self._write_downloaded_file(
                state.remote_src_file_content,
                state.source_target)

            state.set_file_status(state.source_target.rel_path, local_src_md5,
                                  state.remote_src_file_cyphered_md5)

            state.skip_remote_source_remove = True

        return ACTION_CHECK_REMOTE_DEST_FILE

    def check_remote_dest_file(self, state, remote_dest_cyphered_md5):
        if remote_dest_cyphered_md5 is None:
            return ACTION_UPLOAD_DEST_FILE

        if state.destination_target.remote_md5 == remote_dest_cyphered_md5:
            current_local_dest_md5 = state.get_current_local_dest_md5()

            if state.destination_target.local_md5 == current_local_dest_md5:
                state.set_file_status(state.destination_target.rel_path,
                                      current_local_dest_md5,
                                      remote_dest_cyphered_md5)

                _logger.debug('Remote dest file is equal to local file. (1)')

                # no need to upload, go to the next step
                return ACTION_REMOVE_REMOTE_SRC_FILE

            return ACTION_UPLOAD_DEST_FILE

        _logger.debug('Don\t know if remote dest file is the same or if remote'
                      ' hash is different, download it and check.')

        return ACTION_RISK_OF_CONFLICT_REMOTE_DEST_FILE

    def conflict_remote_dest_file(self, state, remote_dest_file_content,
                                  remote_dest_cyphered_md5):

        if remote_dest_file_content is None:
            return ACTION_UPLOAD_DEST_FILE

        remote_uncyphered_md5 = self._compute_md5_hash(
            remote_dest_file_content)
        remote_dest_file_content.seek(0)

        current_local_dest_md5 = state.get_current_local_dest_md5()

        if current_local_dest_md5 != remote_uncyphered_md5:
            _logger.debug('Remote dest file is different from local. '
                          'Conflict!')

            conflict_name = self._generate_conflicting_file_name(
                state.destination_target)
            conflict_path = os.path.join(self.local_path, conflict_name)

            os.rename(os.path.join(self.local_path,
                                   state.destination_target.rel_path),
                      conflict_path)
            self._write_downloaded_file(remote_dest_file_content,
                                        state.destination_target)

            state.add_task(self._create_push_task(conflict_name, True))

        else:
            _logger.debug('Remote dest file is equal to local file. (2)')
            remote_dest_file_content.close()

        state.set_file_status(state.destination_target.rel_path,
                              remote_uncyphered_md5,
                              remote_dest_cyphered_md5)

        return ACTION_REMOVE_REMOTE_SRC_FILE
