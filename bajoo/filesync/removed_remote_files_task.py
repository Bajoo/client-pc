#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .abstract_task import _Task

import errno
import logging
import os

TASK_NAME = 'remote_deletion'

_logger = logging.getLogger(__name__)


class RemovedRemoteFilesTask(_Task):
    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        self._log(_logger, 'Execute task')

        target = self.nodes[0]
        src_path = os.path.join(self.local_path, target.rel_path)

        if not os.path.exists(src_path):
            self._log(_logger, 'The file to delete is not present on the disk:'
                               ' nothing to do.')

            target.set_hash(None, None)
            return

        if target.local_md5 is None:
            self._log(_logger, 'No local information available, recreate on '
                               'server')

            # send back the file
            self._create_push_task(target.rel_path)
            return

        with open(src_path, 'rb') as file_content:
            md5 = self._compute_md5_hash(file_content)

        if target.local_md5 != md5:
            self._log(_logger, 'File has been localy updated, '
                               'recreate on server')

            # send back the file
            self._create_push_task(target.rel_path)
            return

        try:
            os.remove(src_path)
        except (IOError, OSError) as e:
            if e.errno != errno.ENOENT:
                raise

            self._log(_logger, 'The file to delete is not present on the disk:'
                               ' nothing to do.')

        target.set_hash(None, None)
        return
        yield  # make it a generator
