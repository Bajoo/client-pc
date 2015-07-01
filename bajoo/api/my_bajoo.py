# -*- coding: utf-8 -*-
import logging

from .container import Container

_logger = logging.getLogger(__name__)


class MyBajoo(Container):
    """
    This class represent a private share folder between some specific users.
    The user who creates this share will be set as its admin by default,
    then he/she can add access to this share for other users.
    """

    def __init__(self, session, container_id, name):
        Container.__init__(self, session, container_id, name)


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)
