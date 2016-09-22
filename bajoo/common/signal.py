# -*- coding: utf-8 -*-


class Signal(object):
    """Utility class to register and call callbacks.

    It's a variation of the Observer pattern.

    Observers of a signal can "connect" theirs callables to the signal.
    When the signal is "fired", all connected callbacks are called.

    The main difference between this pattern and the Observer pattern is that
    the object handling callbacks is an attribute of the class which own the
    signal, not the class itself.
    Such class can have several signal, each signal representing a distinct
    action (eg: status_changed).

    Example:

        >>> class ObservableElement(object):
        ...     def __init__(self):
        ...         self.status_changed = Signal()
        >>>
        >>> def callback(new_status):
        ...     print('Status has changed: %s' % new_status)
        >>>
        >>> elm = ObservableElement()
        >>>
        >>> # Observer side:
        >>> elm.status_changed.connect(callback)
        >>>
        >>> # observable side:
        >>> elm.status_changed.fire('STATUS OK')
        Status has changed: STATUS OK
    """

    def __init__(self):
        self._handlers = []

    def connect(self, handler):
        """Register a handler/callback to the signal.

        Args:
            handler (callable): handler which will be called each time the
                signal is fired.
        """
        self._handlers.append(handler)

    def fire(self, *args, **kwargs):
        for h in self._handlers:
            h(*args, **kwargs)

    def disconnect(self, handler):
        """Remove/disconnect a callback.

        Args:
            handler (callable): callback to disconnect
        Returns:
            bool: True if the handler was connected; False otherwise.
        """
        try:
            self._handlers.remove(handler)
            return True
        except ValueError:
            return False

    def disconnect_all(self):
        """Remove all handler/callback registered."""
        self._handlers = []
