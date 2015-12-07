#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .abstract_task import _Task
from ..network.errors import HTTPNotFoundError

import logging
import os

TASK_NAME = 'local_deletion'

_logger = logging.getLogger(__name__)


class RemovedTaskMixin(object):
    def _create_a_remove_task(self, rel_path):
        return RemovedLocalFilesTask(self.container,
                                     (rel_path,), self.local_container,
                                     self.display_error_cb,
                                     parent_path=self._parent_path)


class RemovedLocalFilesTask(_Task):

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.target_list[0]

        if os.path.exists(os.path.join(self.local_path, target.rel_path)):
            _logger.debug('File still exists, abort deletion!')

            yield {target.rel_path: (target.local_md5, target.remote_md5)}
            return

        if target.remote_md5 is not None:
            try:
                metadata = yield self.container.get_info_file(target.rel_path)
                remote_cyphered_md5 = metadata['hash']

                if remote_cyphered_md5 == target.remote_md5:
                    _logger.debug('Remove distant file')
                    yield self.container.remove_file(target.rel_path)
                else:
                    _logger.debug('File on server is different, '
                                  'do not remove the distant file')

            except HTTPNotFoundError:
                _logger.debug('The file to delete is already gone:'
                              'nothing to do.')
        else:
            _logger.debug('No local information about the distant file.  File '
                          'will be downloaded again if stil exists on server')

        yield {}
        return
