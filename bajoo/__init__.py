# -*- coding: utf-8 -*-

from .__version__ import __version__  # noqa

from .bajoo_app import BajooApp
from .common import log
from .common import config
from .common.i18n import set_lang
from . import network


def main():
    """Entry point of the Bajoo client."""

    # Start log and load config
    with log.Context():
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
