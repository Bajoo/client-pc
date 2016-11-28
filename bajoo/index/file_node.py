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
