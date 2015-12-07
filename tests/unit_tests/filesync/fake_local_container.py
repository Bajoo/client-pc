# -*- coding: utf-8 -*-

import tempfile
from bajoo.promise.promise import Promise


class FakeModel(object):

    def __init__(self):
        self.path = tempfile.gettempdir()


class FakeLocalContainer(object):

    """STATUS_UNKNOWN = 1
    STATUS_ERROR = 2
    STATUS_STOPPED = 3
    STATUS_PAUSED = 4
    STATUS_STARTED = 5

    _status_textes = {
        STATUS_UNKNOWN: 'Unknown',
        STATUS_ERROR: 'Error',
        STATUS_STOPPED: 'Stopped',
        STATUS_PAUSED: 'Paused',
        STATUS_STARTED: 'Started'
    }"""

    def __init__(self, model, container):
        self.model = FakeModel()

        self.index_on_release = {}
        self.not_updated_index_on_release = set()
        self.updated_index_but_not_in_dict = set()

        self.hash_couple = {}

    def check_path(self):
        raise Exception("Not supposed to be used in task testing")

    def create_folder(self, root_folder_path):
        raise Exception("Not supposed to be used in task testing")

    def _init_index_file(self, path=None):
        raise Exception("Not supposed to be used in task testing")

    def _save_index(self):
        raise Exception("Not supposed to be used in task testing")

    def acquire_index(self, path, item, is_directory=False,
                      bypass_folder=None):

        def executor(on_fulfilled, on_rejected):
            if path in self.hash_couple:
                on_fulfilled({path: self.hash_couple[path]})
            else:
                on_fulfilled({path: (None, None)})

        return Promise(executor)

    def release_index(self, path, new_index=None):
        if new_index is None:
            self.not_updated_index_on_release.add(path)
        else:
            for k, v in new_index.items():
                self.index_on_release[k] = v

            if path not in new_index:
                self.updated_index_but_not_in_dict.add(path)

    def update_index_owner(self, path, new_item):
        raise Exception("Not supposed to be used in task testing")

    def get_remote_index(self):
        raise Exception("Not supposed to be used in task testing")

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
        self.hash_couple[path] = (local_hash, remote_hash, )
