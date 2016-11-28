#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import logging
import os

from .abstract_task import _Task
from ..network.errors import HTTPNotFoundError
from .task_consumer import add_task
from .added_local_files_task import PushTaskMixin

TASK_NAME = 'remote_add'

_logger = logging.getLogger(__name__)


class AddedRemoteTaskMixin(object):

    def _create_added_remote_task(self, rel_path):
        return AddedRemoteFilesTask(self.container,
                                    (rel_path,), self.local_container,
                                    parent_path=self._parent_path)


class AddedRemoteFilesTask(_Task, PushTaskMixin):

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)
        target = self.nodes[0]

        src_path = os.path.join(self.local_path, target.rel_path)

        try:
            result = yield self.container.download(target.rel_path)
            metadata, remote_file = result
            remote_md5 = metadata['hash']
        except HTTPNotFoundError:
            _logger.debug('File disappear from the server.')
            if target.local_md5 is None and os.path.exists(src_path):
                _logger.debug('A new file exists, upload it!')
                with open(src_path, 'rb') as file_content:
                    local_md5 = self._compute_md5_hash(file_content)
                    file_content.seek(0)

                    metadata = yield self.container.upload(target.rel_path,
                                                           file_content)
                    target.set_hash(local_md5, metadata['hash'])
                    return

            target.set_hash(None, None)
            return

        with remote_file:
            if not os.path.exists(src_path):
                _logger.debug('File does not exist, create it.')

                # Make folder
                try:
                    os.makedirs(os.path.dirname(src_path))
                except (IOError, OSError) as e:
                    if e.errno != errno.EEXIST:
                        raise e

                local_md5 = self._write_downloaded_file(remote_file, target)
                target.set_hash(local_md5, remote_md5)
                return

            # compute local md5
            with open(src_path, 'rb') as file_content:
                md5 = self._compute_md5_hash(file_content)

            if md5 == target.local_md5:
                _logger.debug('Local file didn\'t change, overwite.')
                local_md5 = self._write_downloaded_file(remote_file, target)
                target.set_hash(local_md5, remote_md5)
                return

            # compute downloaded md5
            remote_uncyphered_md5 = self._compute_md5_hash(remote_file)

            if md5 == remote_uncyphered_md5:
                _logger.debug('Local and remote files are equals, do nothing.')
                target.set_hash(md5, remote_md5)
                return

            # duplicate
            _logger.debug('Conflict detected, splitting file.')

            conflicting_name = self._generate_conflicting_file_name(target)
            conflicting_path = os.path.join(self.local_path, conflicting_name)
            os.rename(os.path.join(self.local_path, target.rel_path),
                      conflicting_path)
            self._write_downloaded_file(remote_file, target)

        # push the conflict file
        task = self._create_push_task(conflicting_name)
        target.set_hash(remote_uncyphered_md5, metadata['hash'])
        self._release_index()
        result = yield add_task(task)
        self._task_errors.extend(result)

        return
