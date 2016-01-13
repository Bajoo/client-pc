#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
import shutil
import os
import tempfile
import uuid
import logging

from os.path import exists

from bajoo.common.config import _get_config_file_path, load, set, get, \
    _config_parser

"""### TEST CASES ###
    ## load
    config file exist
    config file does not exist

    ##get
    key does not exist
    get a bool value
    get a bool with invalid value
    get an int value
    get an int with invalid value
    get a dict
    get a dict with invalid value
    get a not typed value
    delete an excesting key from file then get it

    ##set
    set a not existing key
    set a None value
    set a string value
    set a not string value
    set without existing file
    set with existing file
"""

backupFile = None


def backupConf(config_path):
    global backupFile

    if not exists(config_path):
        return

    temp_dir = tempfile.gettempdir()
    backupFile = os.path.join(
        temp_dir, "bajoo_unittesting_config_backup" + str(uuid.uuid4()))
    shutil.copy2(config_path, backupFile)


def restoreConf(config_path):
    global backupFile

    # remove the config file generated during the tests
    if exists(config_path):
        os.remove(config_path)

    # no config file existed before the tests
    if backupFile is None:
        return

    shutil.copy2(backupFile, config_path)


def removeBackup():
    global backupFile

    if backupFile is None:
        return

    os.remove(backupFile)
    backupFile = None


class catchLogging(logging.NullHandler):

    def __init__(self):
        logging.NullHandler.__init__(self)
        self.lastLogRecord = None

    def handle(self, record):
        self.lastLogRecord = record

catcher = catchLogging()


def setup_module(module):
    backupConf(_get_config_file_path())
    _logger = logging.getLogger()
    _logger.addHandler(catcher)


def teardown_module(module):
    restoreConf(_get_config_file_path())
    removeBackup()

    logger = logging.getLogger()
    logger.removeHandler(catcher)


class TestConfigLoad(object):

    def setup_method(self, meth):
        catcher.lastLogRecord = None
        _config_parser.remove_section('config')
        _config_parser.add_section('config')

    def test_loadWithExistingFile(self):
        config_path = _get_config_file_path()

        if exists(config_path):
            os.remove(config_path)

        assert catcher.lastLogRecord is None
        load()
        assert catcher.lastLogRecord is not None

    def test_loadWithoutExistingFile(self):
        config_path = _get_config_file_path()

        if exists(config_path):
            os.remove(config_path)

        # create a config file
        set('lang', 'plop')

        assert catcher.lastLogRecord is None
        load()
        assert catcher.lastLogRecord is None

        assert get('lang') == 'plop'


class TestConfigGet(object):

    def setup_method(self, meth):
        catcher.lastLogRecord = None
        _config_parser.remove_section('config')
        _config_parser.add_section('config')

    def test_keyDoesNotExist(self):
        with pytest.raises(KeyError):
            set("plop", 42)

    def test_getABoolValue(self):
        set("autorun", False)
        value = get("autorun")
        assert type(value) is bool and not value

        set("autorun", "False")
        value = get("autorun")
        assert type(value) is bool and not value

        set("autorun", None)
        value = get("autorun")
        assert type(value) is bool and value

    def test_getABoolWithInvalidValue(self):
        set("autorun", False)
        _config_parser.set('config', "autorun", "plop")
        value = get("autorun")
        assert type(value) is bool and value

    def test_getAnIntValue(self):
        set("proxy_port", 42)
        value = get("proxy_port")
        assert type(value) is int and value == 42

        set("proxy_port", "42")
        value = get("proxy_port")
        assert type(value) is int and value == 42

        set("proxy_port", None)
        value = get("proxy_port")
        assert value is None

    def test_getAnIntWithInvalidValue(self):
        set("proxy_port", 42)
        _config_parser.set('config', "proxy_port", "plop")
        value = get("proxy_port")
        assert value is None

    def test_getADictValue(self):
        set("log_levels", "aa=bb;cc=dd")
        value = get("log_levels")
        assert type(value) is dict

        assert "aa" in value
        assert value["aa"] == "bb"

        assert "cc" in value
        assert value["cc"] == "dd"

    def test_getADictWithInvalidValue_test1(self):
        _config_parser.set('config', "log_levels", "plop")
        assert catcher.lastLogRecord is None

        value = get("log_levels")
        assert type(value) is dict
        assert len(value) == 0
        assert catcher.lastLogRecord is not None

    def test_getADictWithInvalidValue_test2(self):
        _config_parser.set('config', "log_levels", "plop;toto=tata")
        assert catcher.lastLogRecord is None

        value = get("log_levels")
        assert type(value) is dict
        assert len(value) == 1
        assert catcher.lastLogRecord is not None

        assert "toto" in value
        assert value["toto"] == "tata"

    def test_getAStringValue(self):
        set("proxy_type", 42)
        value = get("proxy_type")
        assert (type(value) is str or type(value) is unicode) and value == "42"

        set("proxy_type", None)
        value = get("proxy_type")
        assert (type(value) is str or type(value)
                is unicode) and value == "HTTP"

    def test_getAkeyNotPresentInFile(self):
        config_path = _get_config_file_path()

        # delete the file
        if exists(config_path):
            os.remove(config_path)

        # create the file
        set("proxy_port", 42)

        value = get("proxy_type")
        assert (type(value) is str or type(value)
                is unicode) and value == "HTTP"


class TestConfigSet(object):

    def setup_method(self, meth):
        catcher.lastLogRecord = None
        _config_parser.remove_section('config')
        _config_parser.add_section('config')

    def test_keyDoesNotExist(self):
        with pytest.raises(KeyError):
            get("plop")

    def test_noneValueResetToDefault(self):
        set('autorun', False)
        value = get("autorun")
        assert type(value) is bool and not value

        set('autorun', None)
        value = get("autorun")
        assert type(value) is bool and value

    def test_noneValueSetToNone(self):
        set('proxy_port', 42)
        value = get("proxy_port")
        assert type(value) is int and value == 42

        set('proxy_port', None)
        value = get("proxy_port")
        assert value is None

    def test_setAString(self):
        set("lang", "plop")
        value = get("lang")
        assert (type(value) is str or type(value)
                is unicode) and value == "plop"

    def test_setANotString(self):
        set("lang", 42)
        value = get("lang")
        assert (type(value) is str or type(value) is unicode) and value == "42"

    def test_setWithoutExistingFile(self):
        config_path = _get_config_file_path()

        if exists(config_path):
            os.remove(config_path)

        set("lang", "plop")
        value = get("lang")
        assert (type(value) is str or type(value)
                is unicode) and value == "plop"

    def test_setWithExistingFile(self):
        config_path = _get_config_file_path()

        if exists(config_path):
            os.remove(config_path)

        # create the file
        set("lang", "plop")

        # overwrite the file
        set("autorun", True)

        value = get("lang")
        assert (type(value) is str or type(value)
                is unicode) and value == "plop"

        value = get("autorun")
        assert type(value) is bool and value
