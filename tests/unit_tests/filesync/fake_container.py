# -*- coding: utf-8 -*-

from bajoo.promise.promise import Promise
from bajoo.network.errors import HTTPNotFoundError


class FakeHTTPNotFoundError(HTTPNotFoundError):

    def __init__(self):
        self.err_code = 404
        self.err_description = "not found"
        self.err_data = "fake"
        self.code = 123
        self.reason = "because"
        self.request = "GET"


class Fake_container(object):

    def __init__(self):
        self.error = None
        self.name = "Fake Container !"

        #
        self.remote_hash = {}

        # result
        self.upload_list = []
        self.info_list = []
        self.removed_list = []
        self.downloaded_list = []

    def __repr__(self):
        return "this is a fake container"

    def _get_encryption_key(self):
        raise Exception("Not supposed to be used in task testing")

    def _encrypt_and_upload_key(self, key, use_local_members=False):
        raise Exception("Not supposed to be used in task testing")

    def _generate_key(self, lock_acquired=False):
        raise Exception("Not supposed to be used in task testing")

    def _update_key(self, use_local_members=False):
        raise Exception("Not supposed to be used in task testing")

    @staticmethod
    def _from_json(session, json_object):
        raise Exception("Not supposed to be used in task testing")

    @classmethod
    def create(cls, session, name, encrypted=True):
        raise Exception("Not supposed to be used in task testing")

    @staticmethod
    def find(session, container_id):
        raise Exception("Not supposed to be used in task testing")

    @staticmethod
    def list(session):
        raise Exception("Not supposed to be used in task testing")

    def delete(self):
        raise Exception("Not supposed to be used in task testing")

    def get_stats(self):
        raise Exception("Not supposed to be used in task testing")

    def list_files(self, prefix=None):
        raise Exception("Not yet implemented !")

        # TODO is used in sync task

        return ()

    def get_info_file(self, path):
        self.info_list.append(path)

        if path not in self.remote_hash:
            def executor(on_fulfilled, on_rejected):
                on_rejected(FakeHTTPNotFoundError())
        else:
            def executor(on_fulfilled, on_rejected):
                on_fulfilled({'hash': self.remote_hash[path][0]})

        return Promise(executor)

    def download(self, path):
        self.downloaded_list.append(path)

        if path not in self.remote_hash:
            def executor(on_fulfilled, on_rejected):
                on_rejected(FakeHTTPNotFoundError())
        else:

            def executor(on_fulfilled, on_rejected):
                dico = {"hash": self.remote_hash[path][0]}
                on_fulfilled((dico, self.remote_hash[path][1]))

                del self.remote_hash[path]

        return Promise(executor)

        return path

    def upload(self, path, file):
        self.upload_list.append(path)

        def executor(on_fulfilled, on_rejected):
            on_fulfilled({'hash': str(path) + "HASH_UPLOADED"})

        return Promise(executor)

    def remove_file(self, path):
        self.removed_list.append(path)

        if path not in self.remote_hash:
            def executor(on_fulfilled, on_rejected):
                on_rejected(FakeHTTPNotFoundError())
        else:
            def executor(on_fulfilled, on_rejected):
                on_fulfilled(None)

            del self.remote_hash[path]

        return Promise(executor)

    def inject_remote(self, path, remote_hash, remote_content):
        self.remote_hash[path] = (remote_hash, remote_content,)
