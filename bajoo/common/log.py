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
import datetime
import errno
import logging
import os.path
import sys


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

    Create and open a new file used for log. The name of the file will contains
    the date of the day, and an increment if previous files has been created.

    Returns:
        FileHandler: a valid fileHandler using the log file, or None if the
            file creation has failed.
    """

    # TODO: put the file in a specific folder instead of using the current
    # directory.
    base_name_file = datetime.date.today().strftime('bajoo-%Y.%m.%d')
    log_path = '%s.log' % base_name_file
    counter = 1

    try:
        # Loop until we found a non-existing file.
        while True:
            # Python3 has mode 'x' (creation only), but not Python2.7
            if sys.version_info[0] is 3:
                try:
                    return logging.FileHandler(log_path, mode='x',
                                               encoding='utf-8')
                except FileExistsError as e:  # noqa
                    if e.errno == errno.EEXIST:
                        pass
            else:
                if not os.path.exists(log_path):
                    return logging.FileHandler(log_path, mode='w',
                                               encoding='utf-8')
            counter += 1
            log_path = '%s (%s).log' % (base_name_file, counter)
    except:
        logging.getLogger(__name__).warning('Unable to create the log file',
                                            exc_info=True)


def init():
    """Open the log file and prepare the logging module before first use."""
    root_logger = logging.getLogger()
    stdout_handler = logging.StreamHandler()

    date_format = '%Y-%m-%d %H:%M:%S'
    string_format = '%(asctime)s %(levelname)-7s %(name)s - %(message)s'
    formatter = logging.Formatter(fmt=string_format, datefmt=date_format)

    stdout_handler.setFormatter(formatter)

    if _support_color_output():
        # TODO: set ColorFormatter
        pass
    root_logger.addHandler(stdout_handler)

    file_handler = _get_file_handler()
    if file_handler:
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Before any configuration, all messages should be displayed.
    set_debug_mode(True)


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
