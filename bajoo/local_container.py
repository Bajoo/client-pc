# -*- coding: utf-8 -*-

import errno
import logging
import os
import shutil

from .api.team_share import TeamShare
from .common.i18n import _, N_
from .common.strings import err2unicode
from .index.index_tree import IndexTree
from .index.index_saver import IndexSaver


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
    STATUS_QUOTA_EXCEEDED = 6
    STATUS_WAIT_PASSPHRASE = 7

    _status_textes = {
        STATUS_UNKNOWN: N_('Unknown'),
        STATUS_ERROR: N_('Error'),
        STATUS_STOPPED: N_('Stopped'),
        STATUS_PAUSED: N_('Paused'),
        STATUS_STARTED: N_('Started'),
        STATUS_QUOTA_EXCEEDED: N_('Quota exceeded'),
        STATUS_WAIT_PASSPHRASE: N_('Passphrase needed')
    }

    def __init__(self, model, container):
        self.status = self.STATUS_UNKNOWN
        self.error_msg = None
        self.container = container
        self.model = model
        self.is_moving = False
        # TODO: remove cross-dependency (IndexSaver and Index) at creation.
        self.index_saver = IndexSaver(None, self.model.path, self.model.id)
        self.index = IndexTree(self.index_saver)
        self.index_saver.index_tree = self.index

    def check_path(self):
        """Check that the path is the folder corresponding to the container.

        It must be an accessible folder, and have a valid index file,
        corresponding to the container id.

        Returns:
            boolean: True if all is ok, otherwise False.
        """

        try:
            self.index.load(self.index_saver.load())
        except (OSError, IOError) as e:
            _logger.warn('Check path of container %s failed: %s',
                         self.container.id, err2unicode(e))
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
                self.error_msg = err2unicode(e.strerror)
            return False
        except ValueError:
            _logger.info('Index file %s seems corrupted:' %
                         self.index_saver.get_index_path(),
                         exc_info=True)
            self.index_saver.create_empty_file()

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
                self.status = self.STATUS_ERROR
                self.error_msg = (_('Folder creation failed: %s') %
                                  err2unicode(e.strerror))
                _logger.warn('Folder creation failed (for container %s): %s',
                             self.container.id, err2unicode(e))
                return None

        _logger.info('Creation of folder "%s" for container %s',
                     folder_path, self.container.id)
        self.model.path = folder_path
        self.status = self.STATUS_STOPPED
        return self.model.path

    def get_remote_index(self):
        """Returns the remote part of the index.

        Returns:
            dict: list of files, of the form {'file/name': md5sum}, with md5sum
                the md5 hash of the remote file.
        """

        return self.index.generate_dict_with_remote_hash_only()

    def is_up_to_date(self):
        """
        Returns:
            boolean: True if the sync is started and no operation are ongoing;
                False otherwise.
        """
        if self.status != self.STATUS_STARTED:
            return False

        return not self.index.is_locked()

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

    def get_status(self):
        if self.model.do_not_sync:
            return self.STATUS_STOPPED

        return self.status

    def get_status_text(self):
        return LocalContainer._status_textes.get(
            self.get_status(), _('Unknown'))

    def remove_on_disk(self):
        """Remove the folder synchronised and its content."""
        _logger.info('Remove container of the disk: rm %s', self.model.path)
        shutil.rmtree(self.model.path, ignore_errors=True)

    def get_path(self):
        """Get the absolute path of the container's root folder.

        Returns:
            Text: path of root folder
        """
        return self.model.path
