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
from .errors import ServiceStoppingError, ServiceUnavailableError

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

        # _input and _output are set after the fork. They are different
        # objects in different process. The child's '_input' connexion match
        # the parent '_output' connexion, and vice-versa.
        self._input = None  # multiprocess.Connexion
        self._output = None  # multiprocess.Connexion

        # Before using a pipe, the corresponding Condition must be acquired.
        self._task_condition = multiprocessing.Condition()
        self._result_condition = multiprocessing.Condition()

        # number of task in the pipe. Protected by _task_condition
        self._task_counter = multiprocessing.Value('i', 0, lock=False)
        # number of result in the pipe. Protected by _result_condition
        self._result_counter = multiprocessing.Value('i', 0, lock=False)

        # Used for 'notify+send' operations, and for raising the STOP flag.
        self._send_task_lock = multiprocessing.Lock()
        self._send_result_lock = multiprocessing.Lock()

        # _stop_event must be set only when all locks are acquired.
        # Lock order: task_cond -> result_cond -> task_lock -> result_lock
        self._stop_event = multiprocessing.Event()

        # Dict accessible only from the main process.
        # The key is a unique task id, and the value is the related promise.
        # It must be protected by "self._lock_promises"
        self._ongoing_promises = {}
        self._lock_promises = None  # threading.Lock

    def start(self):
        """Create the new process, the lobby thread, and start them."""
        # Pipe: Encryption process --> Main process
        parent_input, child_output = multiprocessing.Pipe(duplex=False)

        # Pipe doesn't support transmission of file descriptor (which is
        # required to send files to GPG)
        # Instead, we use local unix socket.
        authkey = multiprocessing.current_process().authkey
        with closing(Listener(None, None, 1, authkey)) as listener:
            self._process = multiprocessing.Process(
                target=_EncryptionProcess.run, name='Bajoo encryption',
                args=(parent_input, child_output, listener.address,
                      self._task_condition, self._result_condition,
                      self._task_counter, self._result_counter,
                      self._send_task_lock, self._send_result_lock,
                      self._stop_event))
            self._process.start()

            # Connection: Main process --> Encryption process
            self._output = listener.accept()

        child_output.close()
        self._input = parent_input
        self._lock_promises = threading.Lock()

        self._lobby_thread = threading.Thread(target=self._run_lobby_thread,
                                              name='Encryption Lobby')
        self._lobby_thread.daemon = True
        self._lobby_thread.start()

    def _send_stop_event(self):
        with self._send_task_lock:
            if self._stop_event.is_set():
                return False  # Event already sent.
            with self._send_result_lock:
                with self._task_condition:
                    with self._result_condition:
                        self._stop_event.set()
                        self._result_condition.notify_all()
                    self._task_condition.notify_all()
        return True

    def stop(self):
        """Stop encryption process and the lobby thread."""
        if not self._send_stop_event():
            return

        with self._result_condition:
            self._input.close()
        with self._task_condition:
            self._output.close()
        self._process.join()
        self._lobby_thread.join()
        self._process = None

    def execute_task(self, task, *args, **kwargs):
        """Send task to encryption process.

        This method is thread-safe

        Args:
            task (callable): Callable object. Must be pickeable.
            *args (list): Args passed to callable. Must be picklable objects.
            **kwargs (dict): Keyword args passed to callable. They must be
                picklable objects.
        Returns:
            Promise[?]: promised task result
        """
        df = Deferred()
        error = None
        with self._send_task_lock:
            if self._stop_event.is_set():
                _logger.log(5, 'Encryption service stopping. '
                               'Task is rejected.')
                df.reject(ServiceStoppingError())
                return

            with self._task_condition:
                self._task_counter.value += 1
                self._task_condition.notify()
            try:
                send_data(self._output, self._process.pid,
                          id(df), task, args, kwargs)
            except Exception as e:
                _logger.critical('Encryption socket closed due to an '
                                 'unexpected error', exc_info=True)
                error = e
        if error is not None:
            # At this point, there is nothing we can do!
            df.reject(ServiceUnavailableError(error))
            self._send_stop_event()
            return

        with self._lock_promises:
            self._ongoing_promises[id(df)] = df
        return df.promise

    def _check_stop_event(self):
        if self._stop_event.is_set():
            try:
                self._input.close()
            except (EOFError, IOError, OSError):
                pass
            _logger.debug('Encryption service is stopping. '
                          'The lobby thread will stop too.')
            raise ServiceStoppingError()

    def _run_lobby_thread(self):
        """Entry point of the lobby thread.

        The lobby thread run in the main process. It waits for messages (task
        results) from encryption workers, and resolves (or reject) the
        associated promises.
        """
        try:
            while True:
                with self._result_condition:
                    self._check_stop_event()
                    if self._result_counter.value is 0:
                        self._result_condition.wait()
                        self._check_stop_event()

                    if self._result_counter.value is 0:
                        continue  # Thread should not have been awakened

                    try:
                        self._result_counter.value -= 1
                        task_id, success, result = self._input.recv()
                    except Exception as e:
                        _logger.error('Stop encryption lobby thread due to an '
                                      'unexpected socket error', exc_info=True)
                        raise ServiceUnavailableError(e)

                with self._lock_promises:
                    p = self._ongoing_promises.pop(task_id)
                if success:
                    p.resolve(result)
                else:
                    p.reject(result)
        except Exception as stop_reason:
            if isinstance(stop_reason, ServiceUnavailableError):
                self._send_stop_event()
            with self._lock_promises:
                for _id, p in self._ongoing_promises.items():
                    p.reject(stop_reason)


class _EncryptionProcess(object):
    """Main code of the encryption process.

    All code of the encryption process is in this class.

    The encryption process containing a pool of threads, receiving and calling
    operation orders. The encryption process's main thread waits and joins
    others threads.
    """

    def __init__(self, task_condition, result_condition, task_counter,
                 result_counter, send_task_lock, send_result_lock, stop_event):
        self._task_condition = task_condition
        self._result_condition = result_condition
        self._task_counter = task_counter
        self._result_counter = result_counter
        self._send_task_lock = send_task_lock
        self._send_result_lock = send_result_lock
        self._stop_event = stop_event

        self._input = None  # multiprocess.Connexion
        self._output = None  # multiprocess.Connexion

    @classmethod
    def run(cls, parent_in, child_output, input_address, task_condition,
            result_condition, task_counter, result_counter, send_task_lock,
            send_result_lock, stop_event):
        """Entry point of the encryption process

        Args:
            parent_in (Connection): handle to close.
            child_output (Connection): Connection write-only to the lobby
                thread (main process).
            input_address: Address of a local socket (Unix socket or Windows
                Pipe) to open for receiving input data.
            task_condition (Condition): Must be acquired when receiving a
                task from the main process.
            result_condition (Condition): ust be acquired when sending
                result data to the main process.
            task_counter (Value): shared value, containing the number of tasks
                in transit through pipe.
            result_counter (Value): shared value, containing the number of
                tasks in transit through pipe.
            send_task_lock (Lock): Lock required for setting STOP event.
            send_result_lock (Lock): Lock that must be acquired before sending
                result data. It shouldn't be acquired when receiving data.
            stop_event (Event): event raised when the process must stop. It
                can't be set when activity_lock is locked.
        """
        enc_process = cls(task_condition, result_condition, task_counter,
                          result_counter, send_task_lock, send_result_lock,
                          stop_event)
        enc_process._run_process(parent_in, child_output, input_address)

    def _run_process(self, parent_in, child_output, input_address):
        # the logging module behaves differently between Linux and Windows.
        # The best way to deal with that is to reset all handlers, then
        # re-adding them.
        log.reset()

        with log.Context('encryption-process.log'):
            config.load()
            log.set_debug_mode(config.get('debug_mode'))
            log.set_logs_level(config.get('log_levels'))
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

            try:
                self._stop_event.wait()
            except KeyboardInterrupt:
                _logger.info('Keyboard interruption! '
                             'Stop Encryption process ...')
                self._send_stop_event()
            else:
                _logger.debug('Stop encryption event ...')

            # TODO: Kill instances of GnuPG.

            with self._task_condition:
                self._input.close()
            with self._result_condition:
                self._output.close()

            # Threads are daemon. Waiting for them would block until all GPG
            # operations are done, so they are not explicitly "joined".

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

    def _send_stop_event(self):
        with self._send_task_lock:
            if self._stop_event.is_set():
                return  # Event already sent.
            with self._send_result_lock:
                with self._task_condition:
                    with self._result_condition:
                        self._stop_event.set()
                        self._result_condition.notify_all()
                    self._task_condition.notify_all()

    def _cleanup_input(self):
        try:
            self._input.close()
        except (IOError, OSError):
            pass

    def _run_worker_thread(self):
        """Entry point of worker threads

        It waits for orders, execute them, and send result back.
        It loops until the connection is closed.
        """
        _logger.debug('Start "%s"', threading.current_thread().name)
        while True:
            with self._task_condition:
                if self._stop_event.is_set():
                    self._cleanup_input()
                    break

                if self._task_counter.value is 0:
                    self._task_condition.wait()
                    if self._stop_event.is_set():
                        self._cleanup_input()
                        break

                if self._task_counter.value is 0:
                    continue  # Thread should not have been awakened

                try:
                    self._task_counter.value -= 1
                    task_id, action, args, kwargs = recv_data(self._input)
                except Exception:
                    _logger.error('Stop thread "%s" due to an unexpected '
                                  'socket error (input)',
                                  threading.current_thread().name,
                                  exc_info=True)
                    break  # _input has been closed: we must stop

            try:
                _logger.log(5, 'Execute task #%s ...', task_id)
                result = action(*args, **kwargs)
            except Exception as e:
                _logger.log(5, 'Action #%s failed.', task_id)
                task_successful = False
                # Unfortunately, we can't send traceback between process. Only
                # the error itself is sent.
                result = e
            else:
                _logger.log(5, 'Action #%s done.', task_id)
                task_successful = True

            send_stop = False
            with self._send_result_lock:
                if self._stop_event.is_set():
                    break

                with self._result_condition:
                    self._result_counter.value += 1
                    self._result_condition.notify()  # wake up lobby thread.
                try:
                    self._output.send((task_id, task_successful, result))
                except Exception:
                    _logger.error('Stop thread "%s" due to an unexpected '
                                  'socket error (output)',
                                  threading.current_thread().name,
                                  exc_info=True)
                    send_stop = True
            if send_stop:
                self._send_stop_event()
                break

        _logger.debug('Encryption service stopping; Stop "%s"',
                      threading.current_thread().name)
