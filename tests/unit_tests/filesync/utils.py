#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bajoo.promise.promise import Promise
from .fake_container import Fake_container
from .fake_local_container import FakeLocalContainer

import hashlib
import os
import random
import shutil
import string
import tempfile


class TestTaskAbstract(object):

    def setup_method(self, method):
        self.error_string = ""
        self.container = Fake_container()
        self.local_container = FakeLocalContainer(None, None)
        self.result = None
        self.conflict_seed = []
        self.conflict_list = None
        self.file_to_close = []
        self.path_to_remove = []

    def teardown_method(self, method):
        if self.conflict_list is None:
            self.generate_conflict_file_list()

        for path in self.conflict_list:
            try:
                os.remove(path)
            except:
                continue

        for path in self.path_to_remove:
            if not os.path.exists(path):
                continue

            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except:
                    continue
            else:
                try:
                    os.remove(path)
                except:
                    continue

        for f in self.file_to_close:
            try:
                f.descr.close()
            except:
                continue

    def error_append(self, string):
        self.error_string += string

    def add_conflict_seed(self, path):
        self.conflict_seed.append(path)

    def add_file_to_close(self, file):
        self.file_to_close.append(file)

    def add_file_to_remove(self, path):
        self.path_to_remove.append(path)

    def execute_task(self, task):
        gen = task()
        result = None
        while True:
            try:
                if isinstance(result, Promise):
                    result = result.result()

                result = gen.send(result)
            except StopIteration:
                self.result = result
                break
            except Exception as ex:
                result = gen.throw(ex)

        return task

    def generate_conflict_file_list(self):
        self.conflict_list = []

        for path in self.path_to_remove:
            self.conflict_list.extend(
                get_conflict_file_list_from_path(tempfile.gettempdir(), path))

        for f in self.file_to_close:
            self.conflict_list.extend(get_conflict_file_list(f))

        for path in self.conflict_seed:
            self.conflict_list.extend(
                get_conflict_file_list_from_path(tempfile.gettempdir(), path))

        for conflict in self.conflict_list:
            conflict_path = os.path.join(tempfile.gettempdir(), conflict)
            self.path_to_remove.append(conflict_path)

        return self.conflict_list

    def assert_no_error_on_task(self):
        assert self.error_string == ""
        assert self.result is None

    def assert_error_on_task(self, task):
        assert isinstance(self.result, list)
        assert len(self.result) == 1
        assert isinstance(self.result[0], type(task))
        assert self.result[0] is task

    def check_action(self, removed=(), downloaded=(), uploaded=(), getinfo=()):
        assert len(self.container.removed_list) == len(removed)
        assert len(self.container.downloaded_list) == len(downloaded)
        assert len(self.container.upload_list) == len(uploaded)
        assert len(self.container.info_list) == len(getinfo)

        for item in removed:
            assert item in self.container.removed_list

        for item in downloaded:
            assert item in self.container.downloaded_list

        for item in uploaded:
            assert item in self.container.upload_list

        for item in getinfo:
            assert item in self.container.info_list

    def assert_conflict(self, count=0):
        self.generate_conflict_file_list()
        assert len(self.conflict_list) == count

    def assert_index_on_release(self, path, local_hash, remote_hash):
        assert path in self.local_container.index_on_release
        stored_md5 = self.local_container.index_on_release[path]
        assert stored_md5 == (local_hash, remote_hash,)


def assert_content(path, hash):
    local_hash = generate_hash_from_path(path)
    assert local_hash == hash


def get_conflict_file_list(fake_file):
    return get_conflict_file_list_from_path(fake_file.dir, fake_file.filename)


def get_conflict_file_list_from_path(directory, prefix):
    conflict_file_list = []

    for file_name in os.listdir(directory):
        path = os.path.join(directory, file_name)
        if os.path.isfile(path) and file_name.startswith(prefix) and \
           "conflict" in file_name.lower():
            conflict_file_list.append(file_name)

    return conflict_file_list


class FakeFile(object):

    def __init__(self, content=None, dir=None):
        self.descr = tempfile.NamedTemporaryFile(dir=dir)

        if content is None:
            self.content = generate_random_string(55)
        else:
            self.content = content

        if len(self.content) > 0:
            self.descr.write(self.content.encode("utf-8"))
            self.descr.flush()
            self.descr.seek(0)

        self.local_hash = generate_hash(self.descr)
        self.descr.seek(0)

        self.remote_hash = generate_random_string()

        self.dir, self.filename = os.path.split(self.descr.name)

    def writeRandom(self):
        self.descr.seek(0)
        self.content = generate_random_string(55)
        self.descr.write(self.content.encode("utf-8"))
        self.descr.flush()
        self.regenerateHash()

    def writeContent(self, content):
        self.descr.seek(0)
        self.content = content
        self.descr.write(self.content.encode("utf-8"))
        self.descr.flush()
        self.regenerateHash()

    def regenerateHash(self):
        self.descr.seek(0)
        self.local_hash = generate_hash(self.descr)
        self.descr.seek(0)


def generate_random_string(size=16):
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in range(size))


def generate_hash(file_content):
    d = hashlib.md5()
    for buf in file_content:
        d.update(buf)

    return d.hexdigest()


def generate_hash_from_path(path):
    with open(path, "r+b") as file_content:
        return generate_hash(file_content)
