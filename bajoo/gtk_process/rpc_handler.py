# -*- coding: utf-8 -*-

import importlib
from logging import getLogger
import threading
from ..common.signal import Signal
from .placeholder import Placeholder
from .proxy import Proxy

_logger = getLogger(__name__)


# Global RPC Handler, initialized by GtkProcessHandler.
_rpc_handler = None


def get_global_rpc_handler():
    return _rpc_handler


def set_global_rpc_handler(rpc_handler):
    global _rpc_handler
    _rpc_handler = rpc_handler


class RPCHandler(object):
    """Perform action on object located in another process.

    A RPCHandler has two different aspects:
    - It can send tasks to another RPCHandler, located in another process. The
      different actions are available through the methods "rpc_*".
    - It receive such tasks from another RPCHandler, and apply them on local
      objects. The reception is done in an independent thread.

    Attributes:
        on_thread_exit (Signal): fired when the lobby thread is over (caused by
            the close of the pipe_in).
   """

    CALL_BY_NAME = 'CALL_BY_NAME'
    GETATTR = 'GETATTR'
    SETATTR = 'SETATTR'
    CALL = 'CALL'
    DELETE = 'DELETE'

    @staticmethod
    def default_context_exec(f, *args, **kwargs):
        """Default identity function for the execution context of RPC tasks."""
        return f(*args, **kwargs)

    def __init__(self, pipe_in, pipe_out, context_exec=None):
        """RPCHandler constructor.

        Args:
            pipe_in (Pipe): pipe used to receive tasks (and send results).
            pipe_out (Pipe): pipe used to send tasks (and receive results).
            context_exec (Optional[Callable]): if set, function used to set the
                context in which the action should be done.
        """
        self._pipe_in = pipe_in
        self._pipe_out = pipe_out
        self._object_mapping = {}
        self._context_exec = context_exec
        self.on_thread_exit = Signal()

        # Event used by the process thread. It's set when the input pipe is
        # free, and cleared when it's in use.
        self._task_event = threading.Event()
        self._task_event.set()

        if not self._context_exec:
            self._context_exec = self.default_context_exec

        self._thread = threading.Thread(target=self.process_thread,
                                        name='RPC handler')
        self._thread.start()

    def stop(self):
        """Stop the thread."""
        self._pipe_in.close()
        self._pipe_out.close()
        self._task_event.set()
        self._thread.join()
        _logger.debug('RPC Handler stopped')

    def get_by_id(self, ref_id):
        """Get an object locally stored from its ID."""
        return self._object_mapping[ref_id]['ref']

    def _remove_ref(self, ref_id):
        """Decrement the reference counter of an object, or remove it."""
        target = self._object_mapping[ref_id]
        target['count'] -= 1
        if target['count'] <= 0:
            self._object_mapping.pop(ref_id)

    def _add_ref(self, target):
        """Increment the ref counter or register a new object."""
        record = self._object_mapping.get(id(target))
        if record is not None:
            record['count'] += 1
        else:
            record = {'ref': target, 'count': 1}
            self._object_mapping[id(target)] = record

    def process_thread(self):
        try:
            while True:
                # Wait until the current action send the result.
                self._task_event.wait()
                self._task_event.clear()
                try:
                    rpc_message = self._pipe_in.recv()
                except EOFError:
                    break  # _input has been closed: we quit.
                action = rpc_message.pop(0)
                self._context_exec(self._execute_action_and_reply, action,
                                   rpc_message)
        except:
            _logger.exception('RPC Handler operation failed!')
        finally:
            self._pipe_in.close()
            self._pipe_out.close()
            self.on_thread_exit.fire()

    def _execute_action_and_reply(self, action, parameters):
        result = self._execute_action(action, parameters)
        self._pipe_in.send(result)
        self._task_event.set()

    def _execute_action(self, action, parameters):
        if action == RPCHandler.CALL_BY_NAME:
            callable_name, imports, args, kwargs = parameters
            args = self._unwrap_item(args)
            kwargs = self._unwrap_item(kwargs)
            _logger.log(5, 'Execute callable %s', callable_name)

            imported_module = importlib.import_module(imports)
            callable = getattr(imported_module, callable_name)
            try:
                return True, self._wrap_item(callable(*args, **kwargs))
            except Exception as e:
                return False, e
        elif action == RPCHandler.GETATTR:
            instance_id, name = parameters
            _logger.log(5, 'GETATTR action with attr=%s', name)
            try:
                value = getattr(self.get_by_id(instance_id), name)
            except Exception as e:
                return False, e
            return True, self._wrap_item(value)
        elif action == RPCHandler.SETATTR:
            instance_id, name, value = parameters
            value = self._unwrap_item(value)
            _logger.log(5, 'SETATTR action with attr=%s', name)
            try:
                setattr(self.get_by_id(instance_id), name, value)
            except Exception as e:
                return False, e
            return True, None
        elif action == RPCHandler.CALL:
            instance_id, args, kwargs = parameters
            callable = self.get_by_id(instance_id)

            _logger.log(5, 'CALL object "%s"',
                        getattr(callable, '__name__',
                                callable.__class__.__name__))

            args = self._unwrap_item(args)
            kwargs = self._unwrap_item(kwargs)
            try:
                return True, self._wrap_item(callable(*args, **kwargs))
            except Exception as e:
                return False, e
        elif action == RPCHandler.DELETE:
            instance_id, = parameters
            self._remove_ref(instance_id)
            return None
        else:
            _logger.error('Unknown command %s', action)
            return None

    def _unwrap_item(self, item):
        """Replace Placeholder received from pipe."""
        if isinstance(item, Placeholder):
            return item.replace(self)
        elif getattr(item, '__class__', None) is tuple:
            return tuple(self._unwrap_item(value) for value in item)
        elif getattr(item, '__class__', None) is dict:
            return {key: self._unwrap_item(value)
                    for key, value in item.items()}
        elif getattr(item, '__class__', None) is list:
            return [self._unwrap_item(value) for value in item]
        return item

    def rpc_call_by_name(self, callable_name, imports, *args, **kwargs):
        """Call a remote object from its name.

        The callable can be indifferently a function or a class object.

        Args:
            callable_name (str): name of the callable object
            imports (str): full module name containing the callable object
                (eg: 'bajoo.gui.task_bar_icon')
            *args (list): args transmitted to the callable
            **kwargs (dict): kwargs transmitted to the callable
        """
        args = self._wrap_item(args)
        kwargs = self._wrap_item(kwargs)
        self._pipe_out.send([RPCHandler.CALL_BY_NAME, callable_name, imports,
                             args, kwargs])
        return self._handle_rcp_result()

    def rpc_delete(self, object_id):
        """Delete an remote object reference.

        Note that it doesn't delete the object if there is more than one
        reference to it.
        """
        self._pipe_out.send([RPCHandler.DELETE, object_id])
        return self._pipe_out.recv()

    def rpc_call(self, object_id, *args, **kwargs):
        """Call a remotely registered object callable."""
        args = self._wrap_item(args)
        kwargs = self._wrap_item(kwargs)
        self._pipe_out.send([RPCHandler.CALL, object_id, args, kwargs])
        return self._handle_rcp_result()

    def rpc_getattr(self, object_id, name):
        """Get the attribute of a remotely registered object."""
        self._pipe_out.send([RPCHandler.GETATTR, object_id, name])
        return self._handle_rcp_result()

    def rpc_setattr(self, object_id, name, value):
        """Set the attribute of a remotely registered object."""
        value = self._wrap_item(value)
        self._pipe_out.send([RPCHandler.SETATTR, object_id, name, value])
        return self._handle_rcp_result()

    def _wrap_item(self, item):
        """Replace objects by Placeholders before sending them through pipe."""
        if isinstance(item, Proxy):
            return True, Placeholder.from_proxy(item)
        elif hasattr(item, '__dict__'):
            self._add_ref(item)
            return Placeholder(item)
        elif getattr(item, '__class__', None) is tuple:
            return tuple(self._wrap_item(value) for value in item)
        elif getattr(item, '__class__', None) is dict:
            return {key: self._wrap_item(value) for key, value in item.items()}
        elif getattr(item, '__class__', None) is list:
            return [self._wrap_item(value) for value in item]
        return item

    def _handle_rcp_result(self):
        """Receive result from Pipe, and convert it into meaningful objects."""
        status, result = self._pipe_out.recv()
        if not status:
            raise result
        return self._unwrap_item(result)
