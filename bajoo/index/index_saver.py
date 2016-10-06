# -*- coding: utf-8 -*-

import io
import json
import logging
import os
from tempfile import NamedTemporaryFile
import threading
import time

from ..common.fs import hide_file_if_windows, replace_file
from ..common.path import get_cache_dir
from ..common.strings import ensure_unicode

# To avoid index saving after every file change, the software waits
# until activity stops during at least 1.0 seconds
_SAVE_AFTER_INACTIVE_DURING = 1.0

# In the worst case, if activity never stops,
# the index file will be saved every 30 seconds
_MAX_TIMER_RESTART = 30

_logger = logging.getLogger(__name__)


class IndexSaver(object):
    def __init__(self, local_container, directory, model_id):
        self.local_container = local_container

        self.directory = directory
        self.model_id = model_id

        if self.directory:
            ensure_unicode(directory)
            self.index_path = os.path.join(directory,
                                           u'.bajoo-%s.idx' % model_id)

        self.last_update = 0.0
        self.timer_restart_count = 0
        self.short_timer_started = False
        self.short_timer_lock = threading.Lock()
        self.last_timer = None

    def set_directory(self, directory):
        """Set the index directory

        This method will also regenerate the index_path

        Args:
            directory (str): the path of the directory
        """

        self.directory = ensure_unicode(directory)
        self.index_path = os.path.join(directory,
                                       u'.bajoo-%s.idx' % self.model_id)

    def set_model_id(self, model_id):
        """Set the model id

        This method will also regenerate the index_path

        Args:
            model_id: the id of the container where the index is used
        """

        self.model_id = model_id
        self.index_path = os.path.join(self.directory,
                                       u'.bajoo-%s.idx' % model_id)

    def get_index_path(self):
        """Get the index path

        This method will return the index path generated from the directory
        and from the model id
        """

        return self.index_path

    def trigger_save(self, nb_err=0):
        """Trigger a save

        This method is used to indicate if a save is needed.
        It also start the period task.

        Args:
            nb_err (number): If set, indicate that this action is a retry.
                It's used to retry without indefinitely looping over the same
                problem.
        """
        if nb_err >= 6:
            _logger.warning('Stop retrying saving index %s', self.index_path)
            return

        self.last_update = time.time()

        # do not allow two parallel timer
        if self.short_timer_lock.acquire(False):
            self.last_timer = threading.Timer(_SAVE_AFTER_INACTIVE_DURING,
                                              self._short_timer_saving,
                                              args=(nb_err,))
            self.last_timer.start()

    def load(self):
        """Load the index file

        No error management occurs here, it will be manage by local_container
        """

        with io.open(self.index_path, encoding='utf-8') as index_file:
            return json.load(index_file)

    def create_empty_file(self):
        """Create the index file.

        No error management occurs here, it will be manage by local_container
        """
        with io.open(self.index_path, "w", encoding='utf-8') as index_file:
            index_file.write(u'{}')

        self._hide_file_if_win(self.index_path)

    def _short_timer_saving(self, nb_err=0):
        current_time = time.time()
        previous_time = self.last_update + _SAVE_AFTER_INACTIVE_DURING
        self.previous_update = current_time

        if previous_time >= current_time:
            self.timer_restart_count += 1

            if self.timer_restart_count < _MAX_TIMER_RESTART:
                self.last_timer = threading.Timer(_SAVE_AFTER_INACTIVE_DURING,
                                                  self._short_timer_saving,
                                                  args=(nb_err,))
                self.last_timer.start()
                return

        self.timer_restart_count = 0
        self.short_timer_lock.release()
        self._save(nb_err)

    def _save(self, nb_err=0):
        # the file index need to be deleted because python is not able to
        # open write access on a hidden file (windows issue)
        _logger.debug('save index')

        index = self.local_container.index.generate_dict()

        try:
            tmp_index_file = NamedTemporaryFile(dir=get_cache_dir(),
                                                delete=False)
            with tmp_index_file:
                json.dump(index, tmp_index_file)
            replace_file(tmp_index_file.name, self.index_path)
            self._hide_file_if_win(self.index_path)
        except:
            _logger.exception('Unable to save index %s:' % self.index_path)

            self.trigger_save(nb_err+1)

    def _hide_file_if_win(self, index_path):
        try:
            hide_file_if_windows(self.index_path)
        except:
            _logger.warning('Tentative to set HIDDEN file attribute to '
                            '%s failed' % index_path, exc_info=True)

    def stop(self):
        if self.last_timer:
            self.last_timer.cancel()

        # if it fails to get the lock, a timer was running, need to save
        if not self.short_timer_lock.acquire(False):
            self._save()

        self.short_timer_lock.release()
