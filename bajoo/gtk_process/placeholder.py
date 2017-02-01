# -*- coding: utf-8 -*-

from .proxy import Proxy


class Placeholder(object):
    """Represent a process-owned object, during inter-process communication.

    A Placeholder replaces an object that can't easily be transferred from one
    process to another. It's created from one side of the IPC channel, and
    converted into a Proxy object at the other side.

    A placeholder's context is local if the targeted object is located in the
    same process as the placeholder. If the real object exists in another
    process (accessible by a RPCHandler), the placeholder's context is remote.

    The context is automatically swapped during an exchange through IPC.

    Attributes:
        instance_id (int): ID of the object.
        context (str): Indicate if the real object is located (in term of
            process) locally or remotely, relative to the placeholder.
    """

    CONTEXT_LOCAL = 'LOCAL'
    CONTEXT_REMOTE = 'REMOTE'

    def __init__(self, target, context=CONTEXT_LOCAL):
        self.instance_id = id(target)

        self.context = context

    @classmethod
    def from_proxy(cls, proxy):
        """Convert a proxy into a placeholder."""
        instance_id = proxy.__dict__['_id']
        return cls(instance_id, context=cls.CONTEXT_REMOTE)

    def __setstate__(self, state):
        self.instance_id = state['instance_id']
        if state['context'] == self.CONTEXT_LOCAL:
            self.context = self.CONTEXT_REMOTE
        else:
            self.context = self.CONTEXT_LOCAL

    def replace(self, rpc_handler):
        """Replace the placeholder by an object usable.

        Args:
            rpc_handler (RPCHandler): rpc handler used by the proxy.
        Returns:
            Any: The real object If the placeholder's context is local;
                Otherwise, a Proxy object related to the target object.
        """
        if self.context == self.CONTEXT_LOCAL:
            return rpc_handler.get_by_id(self.instance_id)
        return Proxy(self.instance_id, rpc_handler)
