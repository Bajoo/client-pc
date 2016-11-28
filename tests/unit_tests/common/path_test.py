#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import logging
import pytest
import uuid
import os
import sys
from os.path import exists, join

from bajoo.common.path import _ensure_dir_exists, resource_filename

"""### TEST CASES ###
    _ensure_dir_exists, dir exists
    _ensure_dir_exists, dir does not exist, allow to create
    _ensure_dir_exists, dir does not exist, not allow to create

    resource_filename, with sys.frozen and sys.executable set
    resource_filename, with sys.frozen set to None
    resource_filename, with sys.executable set to None
"""


def teardown_module(module):
    logger = logging.getLogger()
    for h in list(logger.handlers):
        logger.removeHandler(h)


class TestEnsure_dir_exists(object):

    def setup_method(self, method):
        logger = logging.getLogger()
        for h in list(logger.handlers):
            logger.removeHandler(h)

    def test_dir_already_exists(self, capsys):
        logging.basicConfig(stream=sys.stdout)

        assert tempfile.gettempdir() is not None
        assert exists(tempfile.gettempdir())
        _ensure_dir_exists(tempfile.gettempdir())
        out, err = capsys.readouterr()
        assert out == '' and err == ''

    def test_dir_does_not_exist_and_allowed_to_create(self, capsys):
        logging.basicConfig(stream=sys.stdout)

        assert tempfile.gettempdir() is not None
        newRandomPath = join(tempfile.gettempdir(), str(uuid.uuid4()))
        assert not exists(newRandomPath)
        _ensure_dir_exists(newRandomPath)
        out, err = capsys.readouterr()
        assert out == '' and err == ''
        os.rmdir(newRandomPath)

    @pytest.mark.skipif(os.geteuid() == 0, reason='this test does not work if'
                        'executed with admin rights')
    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason='do not '
                        'know a directory without write right on windows...')
    def test_dir_does_not_exist_and_not_allowed_to_create(self, capsys):
        logging.basicConfig(stream=sys.stdout)

        # TODO find a way to test it on macos and win

        _ensure_dir_exists("/root/toto")
        out, err = capsys.readouterr()
        assert 'Permission denied' in out and err == ''


frozen_back_up = None
executable_back_up = None


class TestResource_filename(object):

    def setup_method(self, method):
        global frozen_back_up, executable_back_up

        frozen_back_up = getattr(sys, "frozen", None)
        executable_back_up = getattr(sys, "executable", None)

    def teardown_method(self, method):
        global frozen_back_up, executable_back_up

        setattr(sys, "frozen", frozen_back_up)
        setattr(sys, "executable", executable_back_up)

    def test_frozen_and_executable_set(self):
        setattr(sys, "frozen", True)
        setattr(sys, "executable", "plop")

        path = resource_filename("tutu")

        assert path.endswith("tutu")

    def test_frozen_set_to_none(self):
        setattr(sys, "frozen", None)
        setattr(sys, "executable", "plop")

        path = resource_filename("titi")

        assert path.endswith("titi")

    def test_executable_set_none(self):
        setattr(sys, "frozen", True)
        setattr(sys, "executable", None)

        path = resource_filename("toto")

        assert path.endswith("toto")
