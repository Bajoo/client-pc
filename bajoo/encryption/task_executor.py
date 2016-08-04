# -*- coding: utf-8 -*-

from contextlib import closing
import ctypes
import logging
import multiprocessing
from multiprocessing.connection import Client, Listener
import os
import threading
from ..common import config
from ..common import log
from ..promise.deferred import Deferred
from .process_transmission import recv_data, send_data

_logger = logging.getLogger(__name__)


class TaskExecutor(object):
    """Process-based service performing asynchronous encryption operations.

    All encryption-related operations are done by the GPG software through the
    gnupg library. All calls are blocking (several minutes for operations on
    large files).
    This class creates a new Process that will handles theses operations,
    and communicates with it.
    The method `_execute_task()` send a task to the process, and returns a
    Promise, hiding all the internal transmission between processes.

    Additionally to the child process, a "lobby" thread is created in the main
    process, for receive results and for resolve promises.

    Noe that this class contains only code executed by the parent process. All
    code executed by the encryption process is located in the
    `_EncryptionProcess` class.


    Both process communicate with two Connection object:
    - an Unix socket or a Windows Pipe (Parent -> Child)
    - an unidirectional Pipe (Child -> Parent).

    From the main process to the encryption workers, the messages sent uses the
    format:
    `[task_id, task, args, kwargs]`, with:
        - `task_id`: unique id identifying the task
        - `task`: a function or method to execute,
        - `args` and `kwargs`: the arguments and keyword arguments passed to
            the task function.
    The transmission is handled by `process_transmission`, and accept file
    objects (with fileno)

    From the workers to the main process, messages have the form:
    `[task_id, status, result]`, with:
        - `task_id`: unique id identifying the task
        - `result`: a boolean telling if the promise should be resolved (True),
            or rejected (False)
        - `result`: either the task's result (if status is True) or the task's
            exception.
    """

    def __init__(self):
        self._process = None
        self._lobby_thread = None  # only in main process
        self._input = None  # multiprocess.Connexion
        self._output = None  # multiprocess.Connexion
        self._lock_output = None  # threading.Lock

        # _in, _out and both locks are set after the fork, and so are different
        # objects in different process. The child's '_in' connexion match the
        # parent's '_out' connexion, and vice-versa.

        # dict accessible only from the main process.
        # The key is a unique task id, and the value is the related promise.
        # It must be protected by "self._lock_output"
        self._ongoing_promises = {}

    def start(self):
        """Create the new process, the lobby thread, and start them."""
        multiprocessing.freeze_support()

        # Pipe: Encryption process --> Main process
        parent_input, child_output = multiprocessing.Pipe(duplex=False)

        # Pipe doesn't support transmission of file descriptor (which is
        # required to send files to GPG)
        # Instead, we use local unix socket.
        authkey = multiprocessing.current_process().authkey
        with closing(Listener(None, None, 1, authkey)) as listener:
            self._process = multiprocessing.Process(
                target=_EncryptionProcess.run, name='Bajoo encryption',
                args=(parent_input, child_output, listener.address))
            self._process.start()

            # Connection: Main process --> Encryption process
            self._output = listener.accept()

        child_output.close()
        self._input = parent_input
        self._lock_output = threading.Lock()

        self._lobby_thread = threading.Thread(target=self._run_lobby_thread,
                                              name='Encryption Lobby')
        self._lobby_thread.daemon = True
        self._lobby_thread.start()

    def stop(self):
        """Stop encryption process and the lobby thread."""
        if not self._process:
            return

        with self._lock_output:
            self._output.close()
        self._process.join()
        self._lobby_thread.join()

    def execute_task(self, task, *args, **kwargs):
        """Send task to encryption process.

        Args:
            task (callable): Callable object. Must be pickeable.
            *args (list): Args passed to callable. Must be picklable objects.
            **kwargs (dict): Keyword args passed to callable. They must be
                picklable objects.
        Returns:
            Promise[?]: promised task result
        """
        df = Deferred()
        with self._lock_output:
            self._ongoing_promises[id(df)] = df
            send_data(self._output, self._process.pid,
                      id(df), task, args, kwargs)
        return df.promise

    def _run_lobby_thread(self):
        """Entry point of the lobby thread.

        The lobby thread run in the main process. It waits for messages (task
        results) from encryption workers, and resolves (or reject) the
        associated promises.
        """
        while True:
            try:
                task_id, success, result = self._input.recv()
            except EOFError:
                # TODO: reject ongoing promise ?
                break  # _input has been closed: we quit.

            with self._lock_output:
                p = self._ongoing_promises.pop(task_id)
            if success:
                p.resolve(result)
            else:
                p.reject(result)


class _EncryptionProcess(object):
    """Main code of the encryption process.

    All code of the encryption process is in this class.

    The encryption process containing a pool of threads, receiving and calling
    operation orders. The encryption process's main thread is used
    to wait and join others threads.
    """

    def __init__(self):
        self._lock_in = threading.Lock()
        self._lock_out = threading.Lock()
        self._input = None  # multiprocess.Connexion
        self._output = None  # multiprocess.Connexion

    @classmethod
    def run(cls, parent_in, child_output, input_address):
        """Entry point of the encryption process

        Args:
            parent_in (Connection): handle to close.
            child_output (Connection): Connection write-only to the lobby
                thread (main process).
            input_address: Address of a local socket (Unix socket or Windows
                Pipe) to open for receiving input data.

        """
        cls()._run_process(parent_in, child_output, input_address)

    def _run_process(self, parent_in, child_output, input_address):
        # the logging module behaves differently between Linux and Windows.
        # The best way to deal with that is to reset all handlers, then
        # re-adding them.
        log.reset()
        config.load()
        log.set_debug_mode(config.get('debug_mode'))
        log.set_logs_level(config.get('log_levels'))

        with log.Context('encryption-process.log'):
            parent_in.close()
            self._output = child_output
            self._input = Client(input_address, None,
                                 multiprocessing.current_process().authkey)
            self._make_process_nice()

            worker_threads = []
            for i in range(multiprocessing.cpu_count()):
                t = threading.Thread(target=self._run_worker_thread,
                                     name='Encryption worker #%s' % i)
                t.daemon = True
                worker_threads.append(t)
                t.start()

            for t in worker_threads:
                t.join()
            _logger.info('Stop of Encryption process')

    @staticmethod
    def _make_process_nice():
        """Set the niceness of the current process to the maximum"""
        try:
            if hasattr(os, 'nice'):
                os.nice(40)  # Will always set niceness at max
            elif hasattr(ctypes, 'windll'):
                # Value taken from the microsoft documentation
                IDLE_PRIORITY_CLASS = ctypes.c_uint(0x00000040)

                process = ctypes.windll.kernel32.GetCurrentProcess()
                ctypes.windll.kernel32.SetPriorityClass(process,
                                                        IDLE_PRIORITY_CLASS)
            else:
                _logger.info('Unable to set process to low priority: '
                             'operation not available')
        except Exception:
            _logger.warning('failed to set process to low priority',
                            exc_info=True)

    def _run_worker_thread(self):
        """Entry point of worker threads

        It waits for orders, execute them, and send result back.
        It loops until the connection is closed.
        """
        _logger.debug('Start "%s"', threading.current_thread().name)
        while True:
            try:
                with self._lock_in:
                    task_id, action, args, kwargs = recv_data(self._input)
            except EOFError:
                _logger.debug('Input socket closed; Stop "%s"',
                              threading.current_thread().name)
                break  # _input has been closed: we must stop

            try:
                _logger.log(5, 'Execute task #%s ...', task_id)
                result = action(*args, **kwargs)
            except Exception as e:
                _logger.log(5, 'Action #%s failed.', task_id)

                # Unfortunately, we can't send traceback between process. Only
                # the error itself is sent.
                with self._lock_out:
                    self._output.send((task_id, False, e))
            else:
                _logger.log(5, 'Action #%s done.', task_id)
                with self._lock_out:
                    self._output.send((task_id, True, result))
