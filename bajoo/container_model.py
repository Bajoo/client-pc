# -*- coding: utf-8 -*-


class ContainerModel(object):
    """Model of Container, representation saved on disk.

    This class has no logic. Its only purpose is to contains data about
    a container and the related custom user settings.
    It includes container's id and container's name, as well as user preference
    on synchronization (local path, ignore sync, ...)

    attributes:
        id (str): Id of the container
        name (unicode): container's name
        path (unicode, optional): absolute path of the container folder, if it
            exists.
        type (str) one of 'teamshare' or 'my_bajoo'
        do_not_sync (boolean): if True, the user don't want to sync it on disk,
            even if the path attribute is defined.
    """

    def __init__(self, id, name, path=None, container_type=None,
                 do_not_sync=False):
        """container model constructor.

        Args:
            id (str): container ID
            name (unicode): container's name
            path (unicode, optional): if set, absolute path of the folder
                present on disk.
            container_type (str): one of 'teamshare' or 'my_bajoo'
            do_not_sync (boolean, optional): if True, the container should not
                be sync on the disk. Default to False.
        """
        self.id = id
        self.name = name
        self.path = path
        self.type = container_type

        self.do_not_sync = do_not_sync
