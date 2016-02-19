# -*- coding: utf-8 -*-

import ctypes
import io
import json
import logging
import os
import sys
import threading
import time

from .common.strings import ensure_unicode

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

        self.directory = ensure_unicode(directory)
        self.model_id = model_id
        self.index_path = os.path.join(directory, u'.bajoo-%s.idx' % model_id)

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

    def trigger_save(self):
        """Trigger a save

        This method is used to indicate if a save is needed.
        It also start the period task.
        """
        self.last_update = time.time()

        # do not allow two parallel timer
        if self.short_timer_lock.acquire(False):
            self.last_timer = threading.Timer(_SAVE_AFTER_INACTIVE_DURING,
                                              self._short_timer_saving)
            self.last_timer.start()

    def load(self):
        """Load the index file

        No error management occurs here, it will be manage by local_container
        """

        with io.open(self.index_path, encoding='utf-8') as index_file:
            self.local_container._index = json.load(index_file)

    def create_empty_file(self):
        """Create the index file.

        No error management occurs here, it will be manage by local_container
        """
        with io.open(self.index_path, "w", encoding='utf-8') as index_file:
            index_file.write(u'{}')

        self._hide_file_if_win()

    def _short_timer_saving(self):
        current_time = time.time()
        previous_time = self.last_update + _SAVE_AFTER_INACTIVE_DURING
        self.previous_update = current_time

        if previous_time >= current_time:
            self.timer_restart_count += 1

            if self.timer_restart_count < _MAX_TIMER_RESTART:
                self.last_timer = threading.Timer(_SAVE_AFTER_INACTIVE_DURING,
                                                  self._short_timer_saving)
                self.last_timer.start()
                return

        self.timer_restart_count = 0
        self.short_timer_lock.release()
        self._save()

    def _save(self):
        # the file index need to be deleted because python is not able to
        # open write access on a hidden file (windows issue)
        _logger.debug('save index')
        try:
            os.remove(self.index_path)
        except (OSError, IOError):
            _logger.exception('Unable to remove index %s:' % self.index_path)
        except Exception:
            _logger.exception('Unexpected exception on index removing %s: ' %
                              self.index_path)

        try:
            with open(self.index_path, 'w') as index_file:
                json.dump(self.local_container._index, index_file)
        except (OSError, IOError):
            _logger.exception('Unable to save index %s:' % self.index_path)
        except Exception:
            _logger.exception('Unexpected exception on index saving %s: ' %
                              self.index_path)

        self._hide_file_if_win()

    def _hide_file_if_win(self):
        if sys.platform in ['win32', 'cygwin', 'win64']:
            try:
                # Set HIDDEN_FILE_ATTRIBUTE (0x02)
                ret = ctypes.windll.kernel32.SetFileAttributesW(
                    self.index_path,
                    0x02)
                if not ret:
                    raise ctypes.WinError()
            except:
                _logger.warning('Tentative to set HIDDEN file attribute to '
                                '%s failed' % self.index_path, exc_info=True)

    def stop(self):
        if self.last_timer:
            self.last_timer.cancel()

        # if it fails to get the lock, a timer was running, need to save
        if not self.short_timer_lock.acquire(False):
            self._save()

        self.short_timer_lock.release()
