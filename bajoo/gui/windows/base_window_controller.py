
from ...common.signal import Signal


class BaseWindowController(object):
    """Base class for controllers of top-level windows

    Attributes:
        view
        app (BajooApp)
        destroyed (Signal): fired when the window is about to be destroyed.
    """

    def __init__(self, view_factory, app, *args, **kwargs):
        """Constructor

        Args:
            view_factory (Callable[[BaseWindowController], BaseWindowView])
            app (BajooApp)
            *args (List): optional argument passed to view_factory
            **kwargs (Dict): optional named argument passed to view_factory
        """
        self.view = view_factory(self, *args, **kwargs)

        self.app = app
        self.destroyed = Signal()

    def show(self):
        """Make the window visible and set it in foreground."""
        self.view.show()

    def destroy(self):
        """Close the Window."""
        self.destroyed.fire()
        self.view.destroy()

    def notify_lang_change(self):
        self.view.notify_lang_change()

    def is_in_use(self):
        """Determine if the window is in use.

        The Window is considered in use if it's visible.
        Returns:
            bool: True if visible; false if not.
        """
        return self.view.is_in_use()
