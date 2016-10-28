# -*- coding: utf-8 -*-

from .base_node import BaseNode


class FolderNode(BaseNode):
    """Node representing a classic folder.

    The `remote_state` is always None, as the storage server don't understand
    the notion of folder.
    The `local_state` is set to True when the folder exists on the filesystem.
    """

    def __init__(self, name):
        BaseNode.__init__(self, name)
        self.local_state = True
