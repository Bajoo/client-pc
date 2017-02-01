# -*- coding: utf-8 -*-


class Proxy(object):
    """Proxy of an item through RPC Handler.

    The target object can be a class instance, but also a method.

    All proxy classes transfers every action to the real object, through the
    RPC handler.
    """
    def __init__(self, instance_id, rpc_handler):
        self.__dict__['rpc_handler'] = rpc_handler
        self.__dict__['_id'] = instance_id

    def __del__(self):
        self.__dict__['rpc_handler'].rpc_delete(self.__dict__['_id'])

    def __getattr__(self, item):
        rpc_handler = self.__dict__['rpc_handler']
        return rpc_handler.rpc_getattr(self.__dict__['_id'], item)

    def __setattr__(self, item, value):
        rpc_handler = self.__dict__['rpc_handler']
        return rpc_handler.rpc_setattr(self.__dict__['_id'], item, value)

    def __getstate__(self):
        rpc_handler = self.__dict__['rpc_handler']
        return rpc_handler.rpc_getattr(self.__dict__['_id'], '__getstate__')

    def __call__(self, *args, **kwargs):
        rpc_handler = self.__dict__['rpc_handler']
        return rpc_handler.rpc_call(self.__dict__['_id'], *args, **kwargs)
