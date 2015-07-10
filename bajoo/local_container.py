# -*- coding: utf-8 -*-

import errno
import json
import logging
import os

from .common.i18n import _
from .common.path import default_root_folder

_logger = logging.getLogger(__name__)


class LocalContainer(object):
    """Representation of the local image of the container.

    Attributes:
        id (str): ID of the Bajoo Container
        name (str): Name of the container
        path (str, optional): If set, path of the container folder present on
            the filesystem. If None, the container has no local folder. The
            path is not guaranteed to be valid, and shoudl be checked using
            ``check_folder()``.
        status: One of the 4 status possible. See below.
    """

    STATUS_UNKNOWN = 1
    STATUS_ERROR = 2
    STATUS_STOPPED = 3
    STATUS_PAUSED = 4

    def __init__(self, id, name, path=None):
        self.id = id
        self.name = name
        self.path = path
        self.status = self.STATUS_UNKNOWN
        self.error_msg = None
        self._index = None
        self._container = None

    def check_path(self):
        """Check that the path is the folder corresponding to the container.

        It must be an accessible folder, and have a valid index file,
        corresponding to the container id.

        Returns:
            boolean: True if all is ok, otherwise False.
        """

        index_path = os.path.join(self.path, '.bajoo-%s.idx' % self.id)
        try:
            with open(index_path) as index_file:
                self._index = json.load(index_file)
        except (OSError, IOError) as e:
            self.status = self.STATUS_ERROR

            if e.errno == errno.ENOENT:
                print(self.path)
                if os.path.isdir(self.path):
                    self.error_msg = _('The local folder content seems to have'
                                       ' been deleted.')
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

    def create_folder(self, name):
        """Create a new folder for storing the container's files.

        Set the ``self.path`` attribute.

        Returns:
            str: the path of the created folder. None if an error occurs
        """
        folder_path = os.path.join(default_root_folder(), name)

        try:
            os.mkdir(folder_path)
            self._init_index_file(folder_path)
        except (OSError, IOError) as e:
            if e.errno == errno.EEXIST:
                # TODO test if it's the same index id ?

                base_path = folder_path
                for i in range(2, 100):
                    try:
                        folder_path = '%s (%s)' % (base_path, i)
                        os.mkdir(folder_path)
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

        self.path = folder_path
        self.status = self.STATUS_STOPPED
        return self.path

    def _init_index_file(self, path=None):
        """Create the index file.

        Args:
            path (str, optional): path of the container folder. If None,
            ``self.path`` will be used.
        """
        path = path or self.path
        index_path = os.path.join(path, '.bajoo-%s.idx' % self.id)
        with open(index_path, "w") as index_file:
            index_file.write('{}')
