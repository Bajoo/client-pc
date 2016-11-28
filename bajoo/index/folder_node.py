# -*- coding: utf-8 -*-

from .base_node import BaseNode


class FolderNode(BaseNode):
    """Node representing a classic folder.

    Server-side, folders are implicit and don't exists as entity. As a
    consequence, the `state` attribute is always `None`
    """

    def set_state(self, state):
        if state is not None:
            raise ValueError('FolderNode accepts only None state.')
