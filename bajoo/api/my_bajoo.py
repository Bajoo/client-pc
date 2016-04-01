# -*- coding: utf-8 -*-

from .container import Container


class MyBajoo(Container):
    """
    This class represent a private share folder between some specific users.
    The user who creates this share will be set as its admin by default,
    then he/she can add access to this share for other users.
    """

    def __init__(self, session, container_id, name, encrypted=True):
        Container.__init__(self, session, container_id, name, encrypted)

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        return "<MyBajoo (id=%s, encrypted=%s)>" % (self.id, self.is_encrypted)
