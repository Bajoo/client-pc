# -*- coding: utf-8 -*-

"""Manages settings and config file.

Manages the settings of the program.
Settings are loaded from a configuration file. If they don't exists, default
values are provided.
When an option is set, the config file is updated.

Before any use, the module must be initialized by calling ``load()``.
"""

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # Python2
import logging

_logger = logging.getLogger(__name__)


# Default config dict. Values not present in this dict are not valid.
# Each entry contains the type expected, and the default value.
_default_config = {
    # TODO: set default debug_mode to False for stable release
    'debug_mode': {'type': bool, 'default': True}
}

# Actual config parser
_config_parser = None


def _get_config_file_path():
    # TODO: set the file in a specific bajoo data folder.
    return 'bajoo.ini'


def load():
    """Find and load the config file.

    This function must be called before any use of the module.
    """
    global _config_parser

    config_file_path = _get_config_file_path()

    _config_parser = configparser.ConfigParser()
    if not _config_parser.read(config_file_path):
        _logger.warning('Unable to load config file: %s' % config_file_path)
    if not _config_parser.has_section('config'):
        _config_parser.add_section('config')


def get(key):
    """Find and return a configuration entry

    If the entry is not specified in the config file, a default value is
    returned.

    Args:
        key (string): the entry key.
    Returns:
        The corresponding value found.
    Raises:
        KeyError: if the config entry doesn't exists.
    """
    if key not in _default_config:
        raise KeyError
    try:
        if _default_config[key]['type'] is bool:
            return _config_parser.getboolean('config', key)
        elif _default_config[key]['type'] is int:
            return _config_parser.getint('config', key)
        else:
            return _config_parser.get('config', key)
    except configparser.NoOptionError:
        return _default_config[key]['default']


def set(key, value):
    """Set a configuration entry.

    Args:
        key (string): the entry key.
        value: the new value to set. It will be converted to string.
    Raises:
        KeyError: if the config entry is not valid.
    """
    if key not in _default_config:
        raise KeyError
    _config_parser.set('config', key, str(value))
    config_file_path = _get_config_file_path()
    try:
        with open(config_file_path, 'w') as config_file:
            _config_parser.write(config_file)
        _logger.debug('Config file modified.')
    except IOError:
        _logger.warning('Unable to write in the config file', exc_info=True)


def main():
    logging.basicConfig()
    load()
    debug_mode = get('debug_mode')
    print('"debug_mode" config is %s (type %s).'
          % (debug_mode, type(debug_mode)))
    try:
        get('foo')
    except KeyError:
        print("The key foo doesn't exists, as expected")
    set('debug_mode', False)
    debug_mode = get('debug_mode')
    print('debug_mode should now be false: %s (type %s)'
          % (debug_mode, type(debug_mode)))


if __name__ == "__main__":
    main()
