# -*- coding: utf-8 -*-

import logging
import multiprocessing
import re
import sys
from bajoo.common import config, log
from .rpc_handler import (RPCHandler, get_global_rpc_handler,
                          set_global_rpc_handler)

_logger = logging.getLogger(__name__)


class GtkProcessHandler(object):
    """Handler of GTK process.

    It creates the new Process, starts it, and set the communication channel
    between the two processes.
    When the process is started, the global RPC Handler is created, and the
    function `proxy_factory()` can be used.

    `start()` and `stop()` are replicated over the Gtk process, and all threads
    used for communication.
    """
    def __init__(self):
        self._process = None
        self._pipe_in = None
        self._pipe_out = None

    def start(self):
        pipes_in = multiprocessing.Pipe()
        pipes_out = multiprocessing.Pipe()
        self._process = multiprocessing.Process(
            target=GtkProcess.run, args=pipes_out + pipes_in)
        self._process.name = 'bajoo-gtk3-gui'
        self._process.start()
        pipes_in[0].close()
        pipes_out[0].close()
        self._pipe_in = pipes_in[1]
        self._pipe_out = pipes_out[1]

        set_global_rpc_handler(RPCHandler(self._pipe_in, self._pipe_out))

    def stop(self, join=True):
        self._pipe_in.close()
        self._pipe_out.close()

        _logger.debug('Stop GTK Process handler ...')
        if join:
            rpc_handler = get_global_rpc_handler()
            rpc_handler.stop()
            set_global_rpc_handler(None)
            self._process.join()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class GtkProcess(object):
    """Entry point code of the Gtk process.

    Set the RPC handler from the gtk side, and start the Gtk main loop.
    """

    def __init__(self, pipe_in, pipe_out):
        self._pipe_in = pipe_in
        self._pipe_out = pipe_out

    @classmethod
    def run(cls, child_in_fd, parent_in_fd, child_out_fd, parent_out_fd):
        """Static entry point for Gtk3 GUI process."""
        parent_in_fd.close()
        parent_out_fd.close()

        # Force reload of all gui-related modules.
        # It'll detect the GTK3 classes hidden from the main process.
        pattern = re.compile('^bajoo.gui')
        for module in list(sys.modules):
            if pattern.match(module):
                del sys.modules[module]

        log.reset()
        with log.Context('gtk-process.log'):
            config.load()
            log.set_debug_mode(config.get('debug_mode'))
            log.set_logs_level(config.get('log_levels'))

            instance = cls(child_in_fd, child_out_fd)
            instance._run()

    def _run(self):
        # The GTK 3.0 loading must be process-specific, as wxPython also uses
        # GTK, and two instances of GTK can't coexists without trouble.
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GObject

        rpc_handler = RPCHandler(self._pipe_in, self._pipe_out,
                                 GObject.idle_add)
        rpc_handler.on_thread_exit.connect(Gtk.main_quit)
        set_global_rpc_handler(rpc_handler)

        try:
            Gtk.main()
        except KeyboardInterrupt:
            _logger.info('Keyboard interruption! Stop GTK Process')
        else:
            _logger.debug('GTK main loop ended.')
        finally:
            rpc_handler.stop()
            set_global_rpc_handler(None)
