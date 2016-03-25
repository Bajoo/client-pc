# -*- coding: utf-8 -*-

import tempfile
from bajoo.index.index_tree import IndexTree
from bajoo.local_container import LocalContainer


class FakeModel(object):

    def __init__(self):
        self.path = tempfile.gettempdir()
        self.id = 42


class FakeLocalContainer(LocalContainer):

    def __init__(self, model=None, container=None):
        if model is None:
            self.model = FakeModel()
        else:
            self.model = model

        self.container = container
        self.status_stack = []
        self.status = LocalContainer.STATUS_STARTED

        self.index = IndexTree(None)

    def __setattr__(self, name, value):
        self.__dict__[name] = value

        if name == "status":
            self.status_stack.append(value)

    def check_path(self):
        raise Exception("Not supposed to be used in task testing")

    def create_folder(self, root_folder_path):
        raise Exception("Not supposed to be used in task testing")

    def _init_index_file(self, path=None):
        raise Exception("Not supposed to be used in task testing")

    def _save_index(self):
        raise Exception("Not supposed to be used in task testing")

    def update_index_owner(self, path, new_item):
        raise Exception("Not supposed to be used in task testing")

    def get_remote_index(self):
        return {}  # corresponds to an empty container

    def is_up_to_date(self):
        raise Exception("Not supposed to be used in task testing")
        # return True

    def get_stats(self):
        raise Exception("Not supposed to be used in task testing")
        # return 0, 0, 0

    def get_status(self):
        raise Exception("Not supposed to be used in task testing")
        # return self.STATUS_STARTED

    def get_status_text(self):
        raise Exception("Not supposed to be used in task testing")
        # return LocalContainer._status_textes.get(self.STATUS_STARTED)

    def remove_on_disk(self):
        raise Exception("Not supposed to be used in task testing")

    def inject_hash(self, path, local_hash, remote_hash):
        node = self.index.root.get_or_insert_node(path)
        node.set_hash(local_hash, remote_hash)
