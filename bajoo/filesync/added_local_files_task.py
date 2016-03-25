#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import logging
import os

from .abstract_task import _Task
from ..network.errors import HTTPNotFoundError
from .task_consumer import add_task


TASK_NAME = 'local_add'

_logger = logging.getLogger(__name__)


class PushTaskMixin(object):

    def _create_push_task(self, rel_path, create_mode=False):
        return AddedLocalFilesTask(self.container,
                                   (rel_path,), self.local_container,
                                   self.display_error_cb,
                                   parent_path=self._parent_path,
                                   create_mode=create_mode)


class AddedLocalFilesTask(_Task, PushTaskMixin):

    def __init__(self, container, target, local_container,
                 display_error_cb, parent_path=None, create_mode=True):

        _Task.__init__(self, container, target, local_container,
                       display_error_cb, parent_path)

        self.create_mode = create_mode

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.nodes[0]
        src_path = os.path.join(self.local_path, target.rel_path)

        try:
            file_content = open(src_path, 'rb')
        except (IOError, OSError) as err:
            if err.errno != errno.ENOENT:
                raise

            if target.remote_md5 is None:
                try:
                    metadata, remote_file = yield self.container.download(
                        target.rel_path)
                    md5 = self._write_downloaded_file(remote_file, target)

                    target.set_hash(md5, metadata['hash'])
                    return
                except HTTPNotFoundError:
                    pass

            if self.create_mode:
                _logger.debug("The file is gone before we've done"
                              " anything.")

                target.set_hash(None, None)
                return

            # the goal is to raise the exception of the first try/catch
            # that's why it uses specificaly a variable to store the
            # exception.
            raise err

        with file_content:
            md5 = self._compute_md5_hash(file_content)
            file_content.seek(0)

            if md5 == target.local_md5:  # Nothing to do
                _logger.debug('Local md5 hash has not changed. ')

                if target.remote_md5 is not None:
                    target.set_hash(md5, target.remote_md5)
                    return

            if target.remote_md5 is not None:
                # get remote distant md5
                try:
                    metadata = yield self.container.get_info_file(
                        target.rel_path)
                    remote_cyphered_md5 = metadata['hash']
                except HTTPNotFoundError:
                    remote_cyphered_md5 = None

                if remote_cyphered_md5 is None or \
                   remote_cyphered_md5 == target.remote_md5:
                    _logger.debug('No remote file, or remote file is'
                                  ' still the same. So upload!')

                    metadata = yield self.container.upload(target.rel_path,
                                                           file_content)
                    target.set_hash(md5, metadata['hash'])
                    return

            try:
                metadata, remote_file = yield self.container.download(
                    target.rel_path)
            except HTTPNotFoundError:
                _logger.debug('No remote file, So upload!')

                metadata = yield self.container.upload(target.rel_path,
                                                       file_content)
                target.set_hash(md5, metadata['hash'])
                return

        with remote_file:
            remote_uncyphered_md5 = self._compute_md5_hash(remote_file)
            remote_file.seek(0)

            if md5 == remote_uncyphered_md5:
                _logger.debug('Remote file is the same as the local file. No'
                              ' upload, no conflict, such a beautiful world.')

                target.set_hash(md5, metadata['hash'])
                return

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

        if result is not None:
            self._task_errors = (result,)

        return
