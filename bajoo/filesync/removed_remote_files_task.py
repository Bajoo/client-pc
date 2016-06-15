#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .abstract_task import _Task
from .added_local_files_task import PushTaskMixin
from .task_consumer import add_task

import errno
import logging
import os

TASK_NAME = 'remote_deletion'

_logger = logging.getLogger(__name__)


class RemovedRemoteFilesTask(_Task, PushTaskMixin):
    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.nodes[0]
        src_path = os.path.join(self.local_path, target.rel_path)

        if not os.path.exists(src_path):
            _logger.debug('The file to delete is not present on the disk: '
                          'nothing to do.')

            target.set_hash(None, None)
            return

        if target.local_md5 is None:
            _logger.debug('No local information available, recreate on server')

            # send back the file
            task = self._create_push_task(target.rel_path)
            self._release_index()  # do not update the index
            result = yield add_task(task)
            self._task_errors.extend(result)

            return

        with open(src_path, 'rb') as file_content:
            md5 = self._compute_md5_hash(file_content)

        if target.local_md5 != md5:
            _logger.debug('File has been localy updated, '
                          'recreate on server')

            # send back the file
            task = self._create_push_task(target.rel_path)
            self._release_index()  # do not update the index
            result = yield add_task(task)
            self._task_errors.extend(result)

            return

        try:
            os.remove(src_path)
        except (IOError, OSError) as e:
            if e.errno != errno.ENOENT:
                raise

            _logger.debug('The file to delete is not present on the disk: '
                          'nothing to do.')

        target.set_hash(None, None)
        return
