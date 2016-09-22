# -*- coding: utf-8 -*-

from .common.signal import Signal


class AppStatus(object):
    """Global status of the application.

    Attributes:
        value (Enum): One of the valid status possible.
        changed (Signal): fired at each change of `value`
    """

    NOT_CONNECTED = 'NOT_CONNECTED'
    CONNECTION_IN_PROGRESS = 'CONNECTION_PROGRESS'
    SYNC_DONE = 'SYNC_DONE'
    SYNC_IN_PROGRESS = 'SYNC_IN_PROGRESS'
    SYNC_PAUSED = 'SYNC_PAUSED'
    SYNC_STOPPED = 'SYNC_STOPPED'
    SYNC_IN_ERROR = 'SYNC_IN_ERROR'

    def __init__(self, value):
        self._value = value
        self.changed = Signal()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):

        if new_value not in (self.NOT_CONNECTED, self.CONNECTION_IN_PROGRESS,
                             self.SYNC_DONE, self.SYNC_IN_PROGRESS,
                             self.SYNC_PAUSED, self.SYNC_STOPPED,
                             self.SYNC_IN_ERROR):
            raise ValueError('Incorrect AppStatus value')

        # has_changed = self._value != new_value
        self._value = new_value

        # NOTE: The task bar icon doesn't detect state changes of containers.
        # Until now, task bar icons "set_state" was called more often than it
        # should (meaning even if the value wasn't modified). That's enough to
        # keep the menu's icons coherent with the real status.
        # The same behavior is kept until the task bar icon code is fixed.
        # FIXME: don't fire the signal if the value don't change.
        # if has_changed:
        self.changed.fire(new_value)
