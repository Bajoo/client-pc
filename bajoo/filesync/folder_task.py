# -*- coding: utf-8 -*-

import errno
import logging
import os
import stat
import sys
from ..common import config
from ..common.strings import err2unicode
from ..index.file_node import FileNode
from ..index.folder_node import FolderNode
from ..index.hints import ModifiedHint
from ..index.hint_builder import HintBuilder
from .filepath import is_hidden, is_path_allowed

_logger = logging.getLogger(__name__)


class FolderTask(object):
    """Sync class in charge of Folder node.

    The sync only concerns the folder itself, and not its children. If the
    target folder is deleted and has child, the node will be marked "deleted",
    but no practical action will be applied. Each child will receive its own
    "Deleted" hint, and the target folder will be locally removed when the last
    child will be removed.

    The sync is done is two parts:
     - execute() will detect any change and return the state and the children
        list that should be present
     - diff_node_and_apply_result() will takes theses elements and adapt the
        tree by adding/removing nodes (indirectly, through hint).
    """

    def __init__(self, local_container, node):
        self.container = local_container
        self.node = node

        # Hints are copied here, because they are reset before the task
        # execution.
        self.local_hint = self.node.local_hint

    def __repr__(self):
        return u'FolderTask("%s")' % self.node.get_full_path()

    def __call__(self):
        try:
            container_path = self.container.get_path()
            file_child_list, folder_child_list = self.execute(container_path,
                                                              self.node,
                                                              self.local_hint)
        except Exception:
            _logger.exception('%s failed', self)
            self.node.release()
            raise
        with self.container.index_tree.lock:
            self.diff_node_and_apply_result(self.node, None,
                                            file_child_list,
                                            folder_child_list)
            self.node.release()
        yield None

    @classmethod
    def execute(cls, container_path, node, local_hint):
        """Execute the task.

        Note:
            Folders does not exists server-side: there is no remote hint.

        Args:
            container_path (Text): absolute path of the container owning the
                node.
            node (FolderNode): target node
            local_hint (Optional[Hint]): local hint of the target node.
        Returns:
            Tuple[List[Text], List[Text]]: list of file, then list of
                sub-folders present in the target folder.
        """
        src_path = node.get_full_path()
        dir_path = os.path.join(container_path, src_path)
        dir_path = os.path.normpath(dir_path)
        _logger.debug('Sync By FolderTask of "%s" ...', dir_path)

        if not node.exists() and not isinstance(local_hint, ModifiedHint):
            # If the folder is empty, delete it, unless it has been created
            # just now.
            try:
                os.rmdir(dir_path)
            except (IOError, OSError) as e:
                if e.errno is errno.ENOENT:
                    _logger.log(5, 'Folder "%s" is gone.', src_path)
                    return [], []
                if e.errno is errno.ENOTEMPTY:
                    # File has been added.
                    return cls.list_dir(container_path, src_path, local_hint)
                else:
                    raise
            _logger.log(5, 'Empty folder "%s" removed.')
            return [], []
        return cls.list_dir(container_path, src_path, local_hint)

    @staticmethod
    def list_dir(container_path, src_path, local_hint):
        """List elements presents in the directory

        Args:
            container_path (Text): absolute path of the root container folder.
            src_path (Text): path of the folder to list, relative to the root
                container folder.
            local_hint (Hint): hint node. It's used to gives more accurate log
                messages.
        Returns:
            Tuple[List[Text], List[Text]]: list of file, then list of
                sub-folders present in the target folder.
        """
        dir_path = os.path.join(container_path, src_path)
        dir_path = os.path.normpath(dir_path)

        try:
            list_files = os.listdir(dir_path)
        except (OSError, IOError) as e:
            if e.errno == errno.ENOENT:  # No such file or directory
                if isinstance(local_hint, ModifiedHint):
                    _logger.log(5, 'Received an "Added" hint about a folder '
                                   'which does not exists')
                else:
                    _logger.log(5, 'Folder %s is gone.', src_path)
                return [], []
            elif e.errno == errno.ENOTDIR:  # Not a directory
                raise  # TODO: conflict between file and directory ?
            else:
                raise

        file_list = []
        folder_list = []
        for name in list_files:
            rel_path = os.path.join(src_path, name)
            abs_path = os.path.join(container_path, rel_path)

            if config.get('exclude_hidden_files') and is_hidden(abs_path):
                continue

            if sys.platform in ['win32', 'cygwin']:
                rel_path = rel_path.replace('\\', '/')

            if not is_path_allowed(rel_path):
                continue

            try:
                file_stat = os.lstat(abs_path)
            except (OSError, IOError) as e:
                if e.errno == errno.ENOENT:
                    continue  # file disappeared between list_dir() and stat()
                else:
                    _logger.warning('File "%s" unreadable by stat, when '
                                    'listing content of "%s" folder: %s',
                                    src_path, err2unicode(e))
                    continue  # TODO: We shouldn't ignore these files.

            if stat.S_ISDIR(file_stat.st_mode):
                folder_list.append(name)
            elif stat.S_ISREG(file_stat.st_mode):
                file_list.append(name)
            else:
                _logger.info('Non-regular file %s ignored', abs_path)
        return file_list, folder_list

    @staticmethod
    def diff_node_and_apply_result(node, new_state, file_child_list,
                                   folder_child_list):
        """Make diff between tree's state and actual state, then update tree.

        This method performs all actions updating the index tree:
        - Set the new state value of the folder node
        - Set "Deleted" hints to each child node that disappeared
        - Create and set "Modified" hints to new child element.

        Notes:
            The index tree must be locked before calling this method.

        Args:
            node (FolderNode): target node
            new_state (Optional[Dict]): new state for the target node. Actually
                always None.
            file_child_list (List[Text]): list of name of file child elements.
            folder_child_list (List[Text]): list of name of folder child
                elements.
        """
        folder_path = node.get_full_path()
        _logger.log(5, 'Apply result for FolderTask %s', folder_path)

        node.set_state(new_state)

        child_to_delete = []
        for child in node.children.values():

            # TODO: catch conflict between file and folders
            if child.name in file_child_list:
                file_child_list.remove(child.name)
            elif child.name in folder_child_list:
                folder_child_list.remove(child.name)
            else:
                child_to_delete.append(child)

        if child_to_delete or file_child_list or folder_child_list:
            _logger.log(5,
                        '%s child deleted, %s new file(s) and %s new '
                        'folder(s) in folder %s',
                        len(child_to_delete),
                        len(file_child_list),
                        len(folder_child_list),
                        folder_path)

        for child in child_to_delete:
            HintBuilder.apply_deleted_event(HintBuilder.SCOPE_LOCAL, child)

        for name in file_child_list:
            child = FileNode(name)
            node.add_child(child)
            HintBuilder.apply_modified_event(HintBuilder.SCOPE_LOCAL, child)
        for name in folder_child_list:
            child = FolderNode(name)
            node.add_child(child)
            HintBuilder.apply_modified_event(HintBuilder.SCOPE_LOCAL, child)
