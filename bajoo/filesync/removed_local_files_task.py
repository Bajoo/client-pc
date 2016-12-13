#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .abstract_task import _Task
from ..network.errors import HTTPNotFoundError

import logging
import os

TASK_NAME = 'local_deletion'

_logger = logging.getLogger(__name__)


class RemovedLocalFilesTask(_Task):

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.nodes[0]
        if not hasattr(target, 'rel_path'):
            # On Windows 10, watchdog sometimes detect directory deletion as a
            # file deletion. There is no way to check what was the target (it
            # doesn't exists anymore), other than ignoring deletions on
            # DirectoryNode targets.
            _logger.debug('deleted target is a directory. Nothing to do.')
            return

        if os.path.exists(os.path.join(self.local_path, target.rel_path)):
            _logger.debug('File still exists, abort deletion!')

            self._create_push_task(target.rel_path)
        elif target.remote_md5 is not None:
            try:
                metadata = yield self.container.get_info_file(target.rel_path)
                remote_cyphered_md5 = metadata['hash']

                if remote_cyphered_md5 == target.remote_md5:
                    _logger.debug('Remove distant file')
                    yield self.container.remove_file(target.rel_path)
                    target.set_hash(None, None)
                else:
                    self._create_added_remote_task(target)
                    _logger.debug('File on server is different, '
                                  'do not remove the distant file')

            except HTTPNotFoundError:
                target.set_hash(None, None)
                _logger.debug('The file to delete is already gone:'
                              'nothing to do.')
        else:
            self._create_added_remote_task(target)
            _logger.debug('No local information about the distant file.  '
                          'File will be downloaded again if stil exists on'
                          ' server')

        return
