# -*- coding: utf-8 -*-

from .__version__ import __version__  # noqa

from .bajoo_app import BajooApp
from .common import log
from .common import config


def main():
    """Entry point of the Bajoo client."""

    # Start log and load config
    log.init()
    config.load()
    log.set_debug_mode(config.get('debug_mode'))
    log.set_logs_level(config.get('log_levels'))

    app = BajooApp()
    app.MainLoop()


if __name__ == "__main__":
    main()
