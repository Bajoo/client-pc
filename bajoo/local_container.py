# -*- coding: utf-8 -*-

import ctypes
import errno
import io
import json
import logging
import os
import shutil
import sys
from threading import RLock

from .api.team_share import TeamShare
from .common.i18n import _
from .promise import Promise


_logger = logging.getLogger(__name__)


class LocalContainer(object):
    """Representation of the local image of the container.

    It also contains (and manages) the local index. The index associate two
    hashes for each file present in the container: the md5 sum of the last
    known local version, and the last known remote version. (These values
    should be identical if the container isn't encrypted).

    The index must be kept coherent, and sync tasks must never works on the
    same part at the same time, to avoid race conditions. To respect this
    constraint, an index part can be reserved.

    Attributes:
        status: One of the 4 status possible. See below.
        container (Container): the corresponding API Container object. If the
            container is not yet loaded, it may be None.
        model (ContainerModel): the local representation of the same container.
            It contains al persistent data.
        is_moving (boolean): if True, the local folder of this container
            is being currently moved, the sync normally has stopped
            and all other operations (which mean all related screens)
            must be blocked.
    """

    STATUS_UNKNOWN = 1
    STATUS_ERROR = 2
    STATUS_STOPPED = 3
    STATUS_PAUSED = 4
    STATUS_STARTED = 5

    _status_textes = {
        STATUS_UNKNOWN: 'Unknown',
        STATUS_ERROR: 'Error',
        STATUS_STOPPED: 'Stopped',
        STATUS_PAUSED: 'Paused',
        STATUS_STARTED: 'Started'
    }

    def __init__(self, model, container):
        self.status = self.STATUS_UNKNOWN
        self.error_msg = None
        self._index = {}
        self._index_lock = RLock()  # Lock both `_index` and `_index_booking`
        self._index_booking = {}
        self.container = container
        self.model = model
        self.is_moving = False

    def check_path(self):
        """Check that the path is the folder corresponding to the container.

        It must be an accessible folder, and have a valid index file,
        corresponding to the container id.

        Returns:
            boolean: True if all is ok, otherwise False.
        """

        index_path = os.path.join(self.model.path,
                                  '.bajoo-%s.idx' % self.model.id)
        try:
            with io.open(index_path, encoding='utf-8') as index_file:
                self._index = json.load(index_file)
        except (OSError, IOError) as e:
            self.status = self.STATUS_ERROR

            if e.errno == errno.ENOENT:
                # TODO: Add a specific message if the folder is empty (or not)
                if os.path.isdir(self.model.path):
                    self.error_msg = _(
                        'The corresponding folder exists, but the Bajoo index '
                        'file is missing.')
                else:
                    self.error_msg = _('The local folder is missing.')
            else:
                self.error_msg = os.strerror(e.errno)
            return False
        except ValueError:
            _logger.info('Index file %s seems corrupted:' % index_path,
                         exc_info=True)
            self._init_index_file()

        self.status = self.STATUS_STOPPED
        return True

    def get_not_existing_folder(self, dest_folder):
        if not os.path.exists(dest_folder):
            return dest_folder

        parent_folder = os.path.abspath(os.path.join(dest_folder, os.pardir))
        src_folder_name = os.path.basename(dest_folder)
        index = 1
        folder_name = '%s (%s)' % (src_folder_name, index)

        while os.path.exists(os.path.join(parent_folder, folder_name)):
            index += 1
            folder_name = '%s (%s)' % (src_folder_name, index)

        return os.path.join(parent_folder, folder_name)

    def create_folder(self, root_folder_path):
        """Create a new folder for storing the container's files.

        Set the ``self.path`` attribute.

        Returns:
            str: the path of the created folder. None if an error occurs
        """

        name = self.container.name
        if self.model.path:
            folder_path = self.model.path
        elif isinstance(self.container, TeamShare):
            folder_path = os.path.join(root_folder_path, _('Shares'), name)
        else:
            folder_path = os.path.join(root_folder_path, name)

        try:
            os.makedirs(folder_path)
            self._init_index_file(folder_path)
        except (OSError, IOError) as e:
            if e.errno == errno.EEXIST:
                # TODO test if it's the same index id ?

                base_path = folder_path
                for i in range(2, 100):
                    try:
                        folder_path = '%s (%s)' % (base_path, i)
                        os.mkdir(folder_path)
                        self._init_index_file(folder_path)
                        break
                    except (OSError, IOError) as e:
                        if e.errno == errno.EEXIST:
                            pass  # TODO test if it's the same index id ?
                        else:
                            raise
            else:
                self.status = self.STATUS_ERROR
                self.error_msg = (_('Folder creation failed: %s') %
                                  os.strerror(e.errno))
                return None

        self.model.path = folder_path
        self.status = self.STATUS_STOPPED
        return self.model.path

    def _init_index_file(self, path=None):
        """Create the index file.

        Args:
            path (str, optional): path of the container folder. If None,
            ``self.path`` will be used.
        """
        path = path or self.model.path
        index_path = os.path.join(path, '.bajoo-%s.idx' % self.model.id)
        with io.open(index_path, "w", encoding='utf-8') as index_file:
            index_file.write(u'{}')
        if sys.platform == 'win32':
            try:
                # Set HIDDEN_FILE_ATTRIBUTE (0x02)
                ret = ctypes.windll.kernel32.SetFileAttributesW(index_path,
                                                                0x02)
                if not ret:
                    raise ctypes.WinError()
            except:
                _logger.warning('Tentative to set HIDDEN file attribute to '
                                '%s failed' % index_path, exc_info=True)

    def _save_index(self):
        index_path = os.path.join(self.model.path,
                                  '.bajoo-%s.idx' % self.model.id)
        try:
            with open(index_path, 'w+') as index_file:
                json.dump(self._index, index_file)
        except (OSError, IOError):
            _logger.exception('Unable to save index %s:' % index_path)

    def acquire_index(self, path, item, is_directory=False,
                      bypass_folder=None):
        """Acquire a part of the index, and returns corresponding values.

        Marks the path as 'acquired', and associate an item to it.
        If the path correspond to some hashes, these hashes are returned.

        The result is returned encapsulated in a Promise: the promise is
        resolved as soon as the index is acquired.

        Args:
            path (str): filename of a file or directory to acquire. It will
                prevents any following calls to acquire the same path (or a
                sub-path if the path correspond to a directory).
            item (*): This object will be associated to the acquired
                path.
            is_directory (boolean): if True, additional checks are
                done to ensures any file in the target folder are reserved.
            bypass_folder (str): If set, the reservation of this folder, and
                parent folders are non-blocking.
        Returns:
            Promise<dict>: The dict contains a list of path (or subpath)
                associated to a couple (local_hash, remote_hash).
        """
        _logger.debug('Acquire index part of %s' % path)
        if path.endswith('/'):
            path = path[:-1]
        parent_path = '/'.join(path.split('/')[:-1]) or '.'

        # Generate paths of all possible parents and itself.
        ancestor_paths = ['.']
        words = path.split('/')
        for i in range(1, len(words) + 1):
            ancestor_paths.append('/'.join(words[:i]))

        with self._index_lock:
            for parent_path in ancestor_paths:
                if parent_path in self._index_booking:
                    bypass = bypass_folder is not None
                    bypass &= (parent_path == '.' or
                               ('%s/' % bypass_folder).startswith(
                                   '%s/' % parent_path))
                    if not bypass:
                        def wait_index(resolve, reject):
                            def cb():
                                p = self.acquire_index(path, item,
                                                       is_directory,
                                                       bypass_folder)
                                p.then(resolve, reject)

                            self._index_booking[parent_path][1].append(cb)

                        return Promise(wait_index)

            if is_directory:
                for p in [p for p in self._index_lock
                          if p.startwith('%s/' % path)]:
                    if '/' in p[len('%s/' % path):]:
                        def wait_index(resolve, reject):
                            def cb():
                                p = self.acquire_index(path, item,
                                                       is_directory,
                                                       bypass_folder)
                                p.then(resolve, reject)

                            self._index_booking[p][1].append(cb)

                        return Promise(wait_index)

            self._index_booking[path] = [item, []]
            if path == '.':
                return Promise.resolve(dict(self._index.items()))
            return Promise.resolve(
                {key: tuple(hashes) for (key, hashes)
                 in self._index.items()
                 if key == path or key.startswith('%s/' % path)})

    def release_index(self, path, new_index=None):
        """Release an acquired index part, and update it.

        Args:
            new_index (dict, optional): If set, replace all values (hashes)
                corresponding to the path and its sub-paths. If None, the
                values are kept intact.
        """
        _logger.debug('Release index part of %s' % path)

        if path.endswith('/'):
            path = path[:-1]
        with self._index_lock:
            if new_index is not None:
                self._index = {
                    key: value for (key, value) in self._index.items()
                    if key != path and not key.startswith('%s/' % path)}
                self._index.update(new_index)
                self._save_index()

            call_list = self._index_booking[path][1]
            del self._index_booking[path]

            # Call next callback
            while call_list and path not in self._index_booking:
                callback = call_list[0]
                del call_list[0]
                self._index_lock.release()
                try:
                    callback()
                finally:
                    self._index_lock.acquire()
            if call_list:
                self._index_booking[path][1] = call_list

    def update_index_owner(self, path, new_item):
        """Update the item associated to a acquired path."""
        if path.endswith('/'):
            path = path[:-1]
        with self._index_lock:
            self._index_booking[path][0] = new_item

    def get_remote_index(self):
        """Returns the remote part of the index.

        Returns:
            dict: list of files, of the form {'file/name': md5sum}, with md5sum
                the md5 hash of the remote file.
        """
        with self._index_lock:
            return {key: self._index[key][1] for key in self._index}

    def is_up_to_date(self):
        """
        Returns:
            boolean: True if the sync is started and no operation are ongoing;
                False otherwise.
        """
        if self.status != self.STATUS_STARTED:
            return False
        with self._index_lock:
            return not bool(self._index_booking)

    def get_stats(self):
        """
        Get the statistics information relating to the local folder.

        Returns <tuple>: (number of folders, number of files, total_size)
        """
        total_size = 0
        n_folders = 0
        n_files = 0

        if self.model.path and os.path.exists(self.model.path):
            for dir_path, dir_names, files_names in os.walk(self.model.path):
                n_folders += 1

                for file_name in files_names:
                    n_files += 1
                    file_path = os.path.join(dir_path, file_name)
                    total_size += os.path.getsize(file_path)

            return n_folders, n_files, total_size

        return 0, 0, 0

    def get_status(self):
        if self.model.do_not_sync:
            return self.STATUS_STOPPED

        return self.status

    def get_status_text(self):
        return LocalContainer._status_textes.get(
            self.get_status(), _('Unknown'))

    def remove_on_disk(self):
        """Remove the folder synchronised and its content."""
        _logger.info('Remove container of the disk: rm %s' % self.model.path)
        shutil.rmtree(self.model.path, ignore_errors=True)
