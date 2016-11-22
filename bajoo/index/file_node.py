# -*- coding: utf-8 -*-

import logging
from .base_node import BaseNode

_logger = logging.getLogger(__name__)


class FileNode(BaseNode):
    """Node representing a single file.

    When not None, the `state` attribute contains two values `local_hash` and
    `remote_hash`, md5 of the file's content. These values should not be None
    if the state exists.
    """

    def set_state(self, state):
        if self.state is not None:
            if set(state.keys()) != {'local_hash', 'remote_hash'}:
                raise ValueError('FileNode state must have two items '
                                 '"local_hash" and "remote_hash"')
        self.state = state

    def get_hashes(self):
        """Get both local and remote hashes of the node.

        Hashes are md5 sums of the file's content.

        Returns:
            Optional[Tuple[str, str]]: tuple of local and remote
                hashes, in that order.
        """
        if not self.state:
            return None, None
        return self.state['local_hash'], self.state['remote_hash']

    def set_hashes(self, local_hash, remote_hash):
        """Set new values for both local and remote hashes.

        Note: hashes must be either both None, or both set to a valid value.

        Args:
            local_hash (Optional[str]): new value for local hash
            remote_hash (Optional[str]): new value for remote hash
        """
        if local_hash is None and remote_hash is None:
            self.state = None
            return

        if local_hash is None or remote_hash is None:
            raise ValueError('either both hashes are None, or both hash must '
                             'exists.')

        if self.state is None:
            self.state = {}
        self.state.update({
            'local_hash': local_hash,
            'remote_hash': remote_hash
        })
