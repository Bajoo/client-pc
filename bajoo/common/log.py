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

import itertools
import logging
import logging.handlers
import os
import os.path
import sys
import time

from . import path as bajoo_path
from .strings import err2unicode


def _support_color_output():
    """Try to guess if the standard output supports color term code.

    Returns:
        boolean: True if we are sure the output supports color; False otherwise
    """
    if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
        if not sys.platform.startswith('win'):
            return True
    return False


class RotatingLogHandler(logging.FileHandler):
    """Log handler who use a file rotated every day.

    '$filename' (passed in __init__) is always the most recent logfile. When
    the program is started, the last log file (if it exists) is renamed to
    '$filename-$date.log', with $date the day of the last modification of the
    file (format %Y.%m.%d).

    If Bajoo is started several times the same day, log files are renamed with
    an increment. '$filename' is the most recent, then '$filename.$today.log',
    followed by '$filename.$today.1.log`, $filename.$today.2.log`, and so on.

    Note that the file rotation is done at midnight and does not require a
    restart.
    """
    def __init__(self, filename, nb_max_files=7):
        """
        Args:
            filename (str): base filename for log file. Ex: "bajoo.log"
            nb_max_files (int, optional): maximum number of log files. When
                there is more files than this values, older files are removed.
        """
        logging.FileHandler.__init__(self, filename, mode='a',
                                     encoding=None)
        self.nb_max_files = nb_max_files
        if os.path.exists(filename):
            stats = os.stat(filename)
            if stats.st_size:
                self.rollover_at = os.stat(filename).st_mtime
                self.do_rollover()
            else:
                self.rollover_at = self.compute_next_rollover()
        else:
            self.rollover_at = self.compute_next_rollover()

    def emit(self, record):
        """Emit a record.

        If needed, performs a rollover before writing the record.
        """
        try:
            if time.time() >= self.rollover_at:
                self.do_rollover()
            logging.FileHandler.emit(self, record)
        except:
            self.handleError(record)

    def compute_next_rollover(self):
        """Work out the rollover time based on the specified time.

        Returns:
            Int: timestamp of the next rollover.
        """
        now = time.time()
        t = time.localtime(now)
        current_hour, current_minute, current_second = t[3:6]
        result = now + 3600 * 24 - (
            (current_hour * 60 + current_minute) * 60 + current_second)

        dst_now = t.tm_isdst
        dst_at_rollover = time.localtime(result).tm_isdst
        if dst_now != dst_at_rollover:
            result += 3600 if dst_now else -3600
        return result

    def rollover(self, src, filename, str_date, extension, inc=0):
        """Recursive renaming function.

        '$filename' is renamed into '$filename.$date.log'
        '$filename.$date.log' is renamed into '$filename.$date.1.log', and so
        on.

        Args:
            src (str): absolute path of the log file. ex: "/log/bajoo.log".
            filename (str): full path, without extension. ex: "/log/bajoo".
        """
        if inc is 0:
            dest = '%s.%s%s' % (filename, str_date, extension)
        else:
            dest = '%s.%s.%s%s' % (filename, str_date, inc, extension)

        if os.path.exists(dest):
            inc += 1
            if (inc + 1) > self.nb_max_files:
                try:
                    os.remove(dest)
                except (OSError, IOError):
                    pass
            else:
                self.rollover(dest, filename, str_date, extension, inc)
        try:
            os.rename(src, dest)
        except (OSError, IOError):
            pass

    def remove_old_files(self, filename):
        """Remove old log files when there are more than the allowed.

        Args:
            filename (str): base part of the filename (without date, nor
                '.log' extension)
        """
        log_dir = bajoo_path.get_log_dir()
        all_log_files = os.listdir(log_dir)

        recent_log_file = []

        # Remove old logs
        for f in all_log_files:
            if f.startswith('bajoo-') or f.startswith('bajoo.log.'):
                # Log formats pre 0.3.18
                try:
                    os.remove(os.path.join(log_dir, f))
                except (OSError, IOError):
                    pass
            elif f.startswith(filename):
                recent_log_file.append(f)

        # 1st sort by date
        recent_log_file = sorted(recent_log_file, reverse=True)

        def key_date(path):
            return path.split('.')[1]

        def key_inc(path):
            split_path = path.split('.')
            return split_path[2] if len(split_path) >= 4 else '0'

        # sort, for each days, by increment
        recent_log_file = [
            p
            for _, one_day_paths
            in itertools.groupby(recent_log_file, key=key_date)
            for p in sorted(one_day_paths, key=key_inc)
            ]

        # Keep "nb_max_files" files, then delete the rest.
        for path in recent_log_file[self.nb_max_files:]:
            try:
                os.remove(os.path.join(log_dir, path))
            except (OSError, IOError):
                pass

    def do_rollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        now = int(time.time())
        dst_now = time.localtime(now).tm_isdst
        time_tuple = time.localtime(self.rollover_at)
        if dst_now != time_tuple.tm_isdst:
            addend = 3600 if dst_now else -3600
            time_tuple = time.localtime(self.rollover_at + addend)
        str_date = time.strftime('%Y-%m-%d', time_tuple)

        filename, extension = os.path.splitext(self.baseFilename)

        self.rollover(self.baseFilename, filename, str_date, extension)
        self.remove_old_files(os.path.basename(filename))

        self.stream = self._open()
        self.rollover_at = self.compute_next_rollover()


def _get_file_handler(filename):
    """Open a new file for using as a log output.

    The handler will automatically rotate the log files, each days, and
    removes files older than 14 days.
    If filename is 'bajoo.log':
    'bajoo.log' is always the current log file (the last one).
    Logs older than a day are renamed with the format 'bajoo.log.YYYY-MM-DD'.

    Args:
        filename (str): name of the log file. Ex: 'bajoo.log'
    Returns:
        FileHandler: a valid fileHandler using the log file, or None if the
            file creation has failed.
    """

    try:
        log_path = os.path.join(bajoo_path.get_log_dir(), filename)
        handler = RotatingLogHandler(log_path)
        return handler
    except:
        try:
            logging.getLogger(__name__).warning(
                'Unable to create the log file', exc_info=True)
        except:
            pass  # We can't log the fact that we can't log in this file.
        return None


class UnicodeFormatter(logging.Formatter):
    """EncodingError-safe formatter.

    Convert formatted exception message into unicode values.
    It avoids unicode errors when OS produces messages not encoded in UTF-8.
    """

    def formatException(self, ei):
        res = logging.Formatter.formatException(self, ei)
        return err2unicode(res)


class ColoredFormatter(UnicodeFormatter):
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
            msg = UnicodeFormatter.formatException(self, ei)
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
        try:
            logging.log(self._level, txt)
        except:
            pass  # There is nothing we can do.

    def flush(self):
        """this flush method does nothing but is required on macos."""
        pass


def _excepthook(exctype, value, traceback):
    try:
        logging.getLogger(__name__).critical(
            'Uncaught exception', exc_info=(exctype, value, traceback))
    except:
        pass  # Avoid recursive logging attempt.


class Context(object):
    """Context class used to open and close log handlers."""

    def __init__(self, filename='bajoo.log'):
        """Prepare a new log context.

        Args:
            filename (str): name fo the log file. default to 'bajoo.log'
        """
        self._stderr = None
        self._stdout = None
        self._filename = filename

    def __enter__(self):
        """Open the log file and prepare the logging module."""

        logging.captureWarnings(True)
        logging.addLevelName(5, 'HIDEBUG')

        root_logger = logging.getLogger()

        date_format = '%Y-%m-%d %H:%M:%S'
        string_format = '%(asctime)s %(levelname)-7s %(name)s - %(message)s'
        formatter = UnicodeFormatter(fmt=string_format, datefmt=date_format)

        self._stderr = sys.stderr
        self._stdout = sys.stdout

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

        file_handler = _get_file_handler(self._filename)
        if file_handler:
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Before any configuration, all messages should be displayed.
        set_debug_mode(True)

        # Log all uncaught exceptions
        sys.excepthook = _excepthook

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release resources (log files, ...)"""
        logging.getLogger(__name__).debug('Stop logger ...')
        logging.shutdown()
        sys.stderr = self._stderr
        sys.stdout = self._stdout


def set_logs_level(levels):
    """Configure a fine-grained log levels for the different modules.

    Args:
        levels (dict): A list of tuple associating a module name and a log
            level. A log level can be a number or a str representing one of the
            logging levels (DEBUG, WARNING, ...). The level name will be
            converted to uppercase.
            Invalids values will be ignored.

    Example:

        >>> # Accept DEBUG logs only for gui and its submodules
        >>> set_logs_level({'bajoo':'info', 'bajoo.gui': 'debug'})

        >>> # Accept DEBUG log in general, but only ERROR logs (and above) for
        >>> # the gui.
        >>> set_logs_level({'bajoo': 10, 'bajoo.gui': 40})
    """
    for (module, level) in levels.items():
        try:
            if isinstance(level, str):
                level = level.upper()
            logging.getLogger(module).setLevel(level)
        except ValueError:
            logger = logging.getLogger(__name__)
            logger.warning('Invalid log level "%s" for logger "%s". '
                           'Will be ignored.',
                           level, module)


def set_debug_mode(debug):
    """Set, or unset the debug log level.

    Note: modules others than bajoo.* usually gives too much information
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

        # gnupg.py is too verbose for our use, even for a debug mode.
        logging.getLogger('bajoo.gnupg').setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('bajoo').setLevel(logging.INFO)


def reset():
    """Reset the root logger (remove handlers and filters)."""
    logger = logging.getLogger()

    for h in logger.handlers[:]:
        logger.removeHandler(h)
    for f in logger.filters[:]:
        logger.removeFilter(f)


def main():
    with Context():
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
        logger.info('The "exit" log entry will be displayed after this line:')

if __name__ == "__main__":
    main()
