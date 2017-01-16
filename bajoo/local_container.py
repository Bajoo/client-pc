# -*- coding: utf-8 -*-

import errno
import logging
import os
import shutil

from .api.team_share import TeamShare
from .common.i18n import _, N_
from .common.strings import err2unicode
from .encryption.errors import PassphraseAbortError
from .index import IndexTree, IndexSaver
from .promise import reduce_coroutine


_logger = logging.getLogger(__name__)


class ContainerStatus(object):
    """Different states possible for a container."""
    SYNC_DONE = 'SYNC_DONE'
    SYNC_PROGRESS = 'SYNC_PROGRESS'
    SYNC_PAUSE = 'SYNC_PAUSE'
    SYNC_STOP = 'SYNC_STOP'
    STATUS_ERROR = 'STATUS_ERROR'
    QUOTA_EXCEEDED = 'QUOTA_EXCEEDED'
    WAIT_PASSPHRASE = 'WAIT_PASSPHRASE'


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

    _status_texts = {
        ContainerStatus.STATUS_ERROR: N_('Error'),
        ContainerStatus.SYNC_STOP: N_('Stopped'),
        ContainerStatus.SYNC_PAUSE: N_('Paused'),
        ContainerStatus.SYNC_PROGRESS: N_('Sync in progress'),
        ContainerStatus.SYNC_DONE: N_('Up to date'),
        ContainerStatus.QUOTA_EXCEEDED: N_('Quota exceeded'),
        ContainerStatus.WAIT_PASSPHRASE: N_('Passphrase needed')
    }

    def __init__(self, model, container):
        self._status = ContainerStatus.SYNC_STOP
        self.error_msg = None
        self.container = container
        self.model = model
        self.is_moving = False
        self.index_tree = IndexTree()
        self.index_saver = IndexSaver(self.index_tree, self.model.path,
                                      self.model.id)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    def check_path(self):
        """Check that the path is the folder corresponding to the container.

        It must be an accessible folder, and have a valid index file,
        corresponding to the container id.

        Returns:
            boolean: True if all is ok, otherwise False.
        """

        try:
            self.index_tree.load(self.index_saver.load())
        except (OSError, IOError) as e:
            _logger.warn('Check path of container %s failed: %s',
                         self.container.id, err2unicode(e))
            self.status = ContainerStatus.STATUS_ERROR

            if e.errno == errno.ENOENT:
                # TODO: Add a specific message if the folder is empty (or not)
                if os.path.isdir(self.model.path):
                    self.error_msg = _(
                        'The corresponding folder exists, but the Bajoo index '
                        'file is missing.')
                else:
                    self.error_msg = _('The local folder is missing.')
            else:
                self.error_msg = err2unicode(e.strerror)
            return False
        except ValueError:
            _logger.info('Index file %s seems corrupted:' %
                         self.index_saver.get_index_path(),
                         exc_info=True)
            self.index_saver.create_empty_file()

        self.status = ContainerStatus.SYNC_STOP
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
            self.index_saver.set_directory(folder_path)
            self.index_saver.create_empty_file()
        except (OSError, IOError) as e:
            if e.errno == errno.EEXIST:
                # TODO test if it's the same index id ?

                base_path = folder_path
                for i in range(2, 100):
                    try:
                        folder_path = '%s (%s)' % (base_path, i)
                        os.mkdir(folder_path)
                        self.index_saver.set_directory(folder_path)
                        self.index_saver.create_empty_file()
                        break
                    except (OSError, IOError) as e:
                        if e.errno == errno.EEXIST:
                            pass  # TODO test if it's the same index id ?
                        else:
                            raise
            else:
                self.status = ContainerStatus.STATUS_ERROR
                self.error_msg = (_('Folder creation failed: %s') %
                                  err2unicode(e.strerror))
                _logger.warn('Folder creation failed (for container %s): %s',
                             self.container.id, err2unicode(e))
                return None

        _logger.info('Creation of folder "%s" for container %s',
                     folder_path, self.container.id)
        self.model.path = folder_path
        self.status = ContainerStatus.SYNC_STOP
        return self.model.path

    def get_remote_index(self):
        """Returns the remote part of the index.

        Returns:
            dict: list of files, of the form {'file/name': md5sum}, with md5sum
                the md5 hash of the remote file.
        """

        return self.index_tree.get_remote_hashes()

    def is_up_to_date(self):
        """Detect if the index tree is up to date.

        Note: errors and container status are ignored.

        Returns:
            boolean: True if the index_tree is sync; False otherwise.
        """
        return not self.index_tree.is_dirty()

    def get_stats(self):
        """
        Get the statistics information relating to the local folder.

        Returns <tuple>: (number of folders, number of files, total_size)
        """
        total_size = 0
        n_folders = 0
        n_files = 0

        _logger.debug('Get stats about container %s ..', self.container.id)
        if self.model.path and os.path.exists(self.model.path):
            for dir_path, dir_names, files_names in os.walk(self.model.path):
                n_folders += 1

                for file_name in files_names:
                    n_files += 1
                    file_path = os.path.join(dir_path, file_name)
                    total_size += os.path.getsize(file_path)

            _logger.log(5, 'Stat collected for container %s',
                        self.container.id)
            return n_folders, n_files, total_size

        return 0, 0, 0

    def get_status_text(self):
        return LocalContainer._status_texts.get(self._status, _('Unknown'))

    def remove_on_disk(self):
        """Remove the folder synchronised and its content."""
        _logger.info('Remove container of the disk: rm %s', self.model.path)
        shutil.rmtree(self.model.path, ignore_errors=True)

    @reduce_coroutine()
    def unlock(self):
        """Unlock the container key and ensure the passphrase is available."""
        try:
            yield self.container._get_encryption_key()
        except PassphraseAbortError:
            self.status = ContainerStatus.WAIT_PASSPHRASE
            self.error_msg = _('No passphrase set.  Syncing is disabled')
            raise
        except Exception as error:
            self.status = ContainerStatus.STATUS_ERROR
            self.error_msg = err2unicode(error)
            raise

        if self.status in (ContainerStatus.STATUS_ERROR,
                           ContainerStatus.WAIT_PASSPHRASE):
            self.status = ContainerStatus.SYNC_STOP
        self.error_msg = None

        yield None

    @property
    def path(self):
        return self.model.path

    @property
    def id(self):
        return self.model.id

    @property
    def name(self):
        return self.model.name

    @property
    def type(self):
        return self.model.type

    @property
    def do_not_sync(self):
        return self.model.do_not_sync
