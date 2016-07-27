#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import shutil
import datetime
import sys

from bajoo.common.path import get_log_dir
from bajoo.common.log import _get_file_handler, ColoredFormatter, Context, \
    OutLogger, _excepthook, set_debug_mode

"""### TEST CASES ###
    XXX at exit routine, check if correctly registered.
        TEST NOT POSSIBLE because py.test clean the atexit routine list...
    at exit routine, check if correctly executed

    _get_file_handler() with not existing file
    _get_file_handler() with existing files
    TODO _get_file_handler(), try to generate an exception BUT how ?

    ColoredFormatter._colorize
    ColoredFormatter.formatTime
    ColoredFormatter.formatException

    init with frozen
    init whithout frozen

    set_debug_mode true
    set_debug_mode false
"""

colorFormater = ColoredFormatter()


class TestLogFormating(object):

    def test_getFileHandler(self):
        shutil.rmtree(get_log_dir())
        file_path = _get_file_handler('test.log')
        assert file_path.baseFilename.endswith('test.log')
        os.remove(file_path.baseFilename)

    def test_colorize_DEBUG(self):
        assert colorFormater._colorize("plop", "DEBUG") == \
            ColoredFormatter._colors['DEBUG'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_INFO(self):
        assert colorFormater._colorize("plop", "INFO") == \
            ColoredFormatter._colors['INFO'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_WARNING(self):
        assert colorFormater._colorize("plop", "WARNING") == \
            ColoredFormatter._colors['WARNING'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_ERROR(self):
        assert colorFormater._colorize("plop", "ERROR") == \
            ColoredFormatter._colors['ERROR'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_CRITICAL(self):
        assert colorFormater._colorize("plop", "CRITICAL") == \
            ColoredFormatter._colors['CRITICAL'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_NAME(self):
        assert colorFormater._colorize("plop", "NAME") == \
            ColoredFormatter._colors['NAME'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_DATE(self):
        assert colorFormater._colorize("plop", "DATE") == \
            ColoredFormatter._colors['DATE'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_EXCEPTION_NAME(self):
        assert colorFormater._colorize("plop", "EXCEPTION_NAME") == \
            ColoredFormatter._colors['EXCEPTION_NAME'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_colorize_EXCEPTION_STR(self):
        assert colorFormater._colorize("plop", "EXCEPTION_STR") == \
            ColoredFormatter._colors['EXCEPTION_STR'] + "plop" + \
            ColoredFormatter._colors['RESET']

    def test_formatTime(self):
        record = logging.LogRecord(
            "record", logging.INFO, "/ici/", 123, "test", None, None)
        formated_record = colorFormater.formatTime(record, "%Y.%m.%d")
        expected_output = "\033[30;1m" + \
            datetime.date.today().strftime('%Y.%m.%d') + \
            ColoredFormatter._colors['RESET']

        assert formated_record == expected_output

    def test_formatException(self):
        try:
            raise Exception()
        except Exception:
            assert ColoredFormatter._colors['EXCEPTION_NAME'] + \
                "Exception" + ColoredFormatter._colors['RESET'] + \
                ":" + ColoredFormatter._colors['EXCEPTION_STR'] + \
                ColoredFormatter._colors['RESET'] in \
                colorFormater.formatException(sys.exc_info())

frozen_back_up = None
handlers_backup = []


class TestLogInit(object):

    def setup_method(self, method):
        global frozen_back_up, handlers_backup

        frozen_back_up = getattr(sys, "frozen", None)
        logger = logging.getLogger()
        handlers_backup = list(logger.handlers)

        for h in handlers_backup:
            logger.removeHandler(h)

    def teardown_method(self, method):
        global frozen_back_up, handlers_backup

        setattr(sys, "frozen", frozen_back_up)
        frozen_back_up = None
        logger = logging.getLogger()

        for h in handlers_backup:
            logger.addHandler(h)

        del handlers_backup[:]

        sys.excepthook = sys.__excepthook__

    def test_initWithFrozen(self):
        setattr(sys, "frozen", True)
        logger = logging.getLogger()

        assert len(logger.handlers) == 0
        assert sys.excepthook is not _excepthook

        with Context():
            assert logging.getLevelName(logging.WARNING + 1) == "STDOUT"
            assert logging.getLevelName(logging.WARNING + 2) == "STDERR"
            assert isinstance(sys.stdout, OutLogger)
            assert isinstance(sys.stderr, OutLogger)

            assert len(logger.handlers) == 1
            assert logging.getLogger().getEffectiveLevel() == logging.INFO
            bajoo_logger = logging.getLogger("bajoo")
            assert bajoo_logger.getEffectiveLevel() == logging.DEBUG
            assert sys.excepthook is _excepthook

    def test_initWithoutFrozen(self):
        setattr(sys, "frozen", False)
        logger = logging.getLogger()

        assert len(logger.handlers) == 0
        assert sys.excepthook is sys.__excepthook__

        with Context():
            assert len(logger.handlers) == 2
            assert logging.getLogger().getEffectiveLevel() == logging.INFO
            bajoo_logger = logging.getLogger("bajoo")
            assert bajoo_logger.getEffectiveLevel() == logging.DEBUG
            assert sys.excepthook is _excepthook

    def test_setDebugTrue(self):
        set_debug_mode(True)
        assert logging.getLogger().getEffectiveLevel() == logging.INFO
        assert logging.getLogger("bajoo").getEffectiveLevel() == logging.DEBUG

    def test_setDebugFalse(self):
        set_debug_mode(False)
        assert logging.getLogger().getEffectiveLevel() == logging.WARNING
        assert logging.getLogger("bajoo").getEffectiveLevel() == logging.INFO
