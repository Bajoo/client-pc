# -*- coding: utf-8 -*-

"""Configuration module of the logs.

This module configure the python ``logging`` module, in order to have useful
and easy to activate logs.

All log entries are written in a file and displayed to the output console.
The name of the file change each time the program is restarted, and contains
the date of the program's start. The file is closed when exiting.

On console output, if the system supports it, logs entries will be colorized.

Exceptions are formatted to display a lot of details, easily readable.
Non-caught exceptions are logged before the program quit.

"""

import atexit
import logging
import logging.handlers
import os.path
import sys

from . import path as bajoo_path


def _on_exit():
    """Add an exit message.

    This function will be called when the programs exit.
    """
    logging.getLogger(__name__).info('Application exiting ...')

atexit.register(_on_exit)


def _support_color_output():
    """Try to guess if the standard output supports color term code.

    Returns:
        boolean: True if we are sure the output supports color; False otherwise
    """
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        if not sys.platform.startswith('win'):
            return True
    return False


def _get_file_handler():
    """Open a new file for using as a log output.

    The handler will automatically rotate the log files, each days, and
    removes files older than 14 days.
    'bajoo.log' is always the current log file (the last one).
    Logs older than a day are renamed with the format 'bajoo.log.YYYY-MM-DD'.

    Returns:
        FileHandler: a valid fileHandler using the log file, or None if the
            file creation has failed.
    """
    try:
        log_path = os.path.join(bajoo_path.get_log_dir(), 'bajoo.log')
        handler = logging.handlers.TimedRotatingFileHandler(
            log_path, when='midnight', backupCount=7)
        handler.doRollover()  # rename 'bajoo.log' of the previous execution.
        return handler
    except:
        logging.getLogger(__name__).warning('Unable to create the log file',
                                            exc_info=True)
        return None


class ColoredFormatter(logging.Formatter):
    """Formatter who display colored messages using ANSI escape codes."""

    _colors = {
        'RESET': '\033[0m',
        'DEBUG': '\033[34m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[31m',
        'NAME': '\033[36m',
        'DATE': '\033[30;1m',
        'EXCEPTION_NAME': '\033[31;1m',
        'EXCEPTION_STR': '\033[37;1m'
    }

    def _colorize(self, msg, color):
        return self._colors.get(color, '') + msg + self._colors.get('RESET')

    def formatTime(self, record, datefmt=None):
        result = logging.Formatter.formatTime(self, record, datefmt)
        return self._colorize(result, 'DATE')

    def formatException(self, ei):
        if hasattr(ei[1], '_origin_stack'):
            # Real stacktrace, before being moved by the Futures.
            msg = ei[1]._origin_stack[:-1]
        else:
            msg = logging.Formatter.formatException(self, ei)
        msg_lines = msg.split('\n')
        last_line = msg_lines[-1]
        result = '\n'.join(msg_lines[:-1]) + '\n'
        result += self._colorize(last_line.split(':')[0], 'EXCEPTION_NAME')
        result += ':' + self._colorize(':'.join(last_line.split(':')[1:]),
                                       'EXCEPTION_STR')
        result += '\n' + repr(ei[1]) + '\n----'
        return result

    def format(self, record):
        record.name = self._colorize(record.name, 'NAME')
        record.levelname = self._colorize(record.levelname, record.levelname)
        return logging.Formatter.format(self, record)


class OutLogger(object):
    """Replacement for sys.stdout and sys.stderr, who log output."""
    def __init__(self, level):
        self._level = level

    def write(self, txt):
        logging.log(self._level, txt)


def _excepthook(exctype, value, traceback):
    logging.getLogger(__name__).critical('Uncaught exception',
                                         exc_info=(exctype, value, traceback))


def init():
    """Open the log file and prepare the logging module before first use."""

    logging.captureWarnings(True)

    root_logger = logging.getLogger()

    date_format = '%Y-%m-%d %H:%M:%S'
    string_format = '%(asctime)s %(levelname)-7s %(name)s - %(message)s'
    formatter = logging.Formatter(fmt=string_format, datefmt=date_format)

    if getattr(sys, 'frozen', False):
        # In frozen mode, this is a GUI app, and there is no stdout.

        STDOUT_LEVEL = logging.WARNING + 1
        STDERR_LEVEL = logging.WARNING + 2

        logging.addLevelName(STDOUT_LEVEL, 'STDOUT')
        logging.addLevelName(STDERR_LEVEL, 'STDERR')

        sys.stdout = OutLogger(STDOUT_LEVEL)
        sys.stderr = OutLogger(STDERR_LEVEL)
    else:
        stdout_handler = logging.StreamHandler()

        if _support_color_output():
            colored_formatter = ColoredFormatter(fmt=string_format,
                                                 datefmt=date_format)
            stdout_handler.setFormatter(colored_formatter)
        else:
            stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

    file_handler = _get_file_handler()
    if file_handler:
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Before any configuration, all messages should be displayed.
    set_debug_mode(True)

    # Log all uncaught exceptions
    sys.excepthook = _excepthook


def set_logs_level(levels):
    """Configure a fine-grained log levels for the differents modules.

    Args:
        levels (dict): A list of tuple associating a module name and a log
            level.
    """
    for (module, level) in levels.items():
        logging.getLogger(module).setLevel(level)


def set_debug_mode(debug):
    """Set, or unset the debug log level.

    Note: modules others than bajoo.* usually gives too much informations
    generally useless. They are not set to DEBUG, even in DEBUG mode.
    If needed, the level log of non-bajoo modules can be set by
    ``set_logs_level()``.

    Args:
        debug (boolean): if True, the bajoo log level will be set to DEBUG.
            If False, it will be set to INFO.
    """
    if debug:
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger('bajoo').setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('bajoo').setLevel(logging.INFO)


def main():
    init()
    logger = logging.getLogger(__name__)
    bajoo_logger = logging.getLogger('bajoo')

    logger.info('This message should be displayed.')
    logger.error('Error messages are red in the console.')
    logger.warning('We also have yellow warning messages.')
    set_debug_mode(False)
    logger.info('This one should never appears.')
    bajoo_logger.debug('Neither this one.')
    bajoo_logger.info('But "bajoo" info message will be displayed.')
    set_debug_mode(True)
    logger.info('The "exit" log entry be displayed will between this line.')

if __name__ == "__main__":
    main()
