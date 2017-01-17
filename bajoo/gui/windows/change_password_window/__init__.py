
from functools import partial
from .change_password_window_controller import ChangePasswordWindowController
from .change_password_window_wx_view import ChangePasswordWindowWxView


# Choices of view implementation
ChangePasswordWindowView = ChangePasswordWindowWxView


ChangePasswordWindow = partial(ChangePasswordWindowController,
                               ChangePasswordWindowView)


__all__ = [
    ChangePasswordWindow
]
