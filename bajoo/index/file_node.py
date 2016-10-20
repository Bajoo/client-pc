# -*- coding: utf-8 -*-

import logging
from .base_node import BaseNode

_logger = logging.getLogger(__name__)


class FileNode(BaseNode):
    """Node representing a single file.

    local and remote states are md5 hashes of the file's content. If None, the
    file don't exists.
    """
    pass
