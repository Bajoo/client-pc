# -*- coding: utf-8 -*-

from .__version__ import __version__  # noqa

import logging
import os
import sys

# an explanation about the use of wxversion is available in the setup.py file.
try:
    import wxversion
    try:
        wxversion.select(['3.0', '2.9', '2.8'])
    except wxversion.VersionError:
        pass
except ImportError:
    pass

from .bajoo_app import BajooApp
from .common import log
from .common import config
from .common.i18n import set_lang
from .common.strings import to_unicode
from . import network


def main():
    """Entry point of the Bajoo client."""

    # Start log and load config
    with log.Context():

        logger = logging.getLogger(__name__)
        cwd = to_unicode(os.getcwd(), in_enc=sys.getfilesystemencoding())
        logger.debug('Current working directory is : "%s"', cwd)

        with network.Context():
            config.load()
            log.set_debug_mode(config.get('debug_mode'))
            log.set_logs_level(config.get('log_levels'))

            # Set the lang from the config file if available
            lang = config.get('lang')
            if lang is not None:
                set_lang(lang)

            app = BajooApp()
            app.run()


if __name__ == "__main__":
    main()
