# -*- coding: utf-8 -*-

import wx

from ..common.i18n import _, N_


class BaseValidator(wx.StaticText):
    """Base class for all bajoo.gui validators.

    Attributes:
        default_err_msg (str, optional): Default value for the error message.
            Should be overridden.

    """

    default_error_message = None

    def __init__(self, parent, target, error_message=None, hide_if_valid=False,
                 **kwargs):
        """Constructor of validator.

        Args:
            parent (wx.Window): parent
            target: element to check the value.
            error_message (str, optional): if set, message to display when the
                validation fails. It will be translated before being displayed.
            hide_if_valid (boolean, optional): If True, this item will be
                hidden if there is not error.
            **kwargs: optional args transmitted to ``wx.StaticText``.
        """
        wx.StaticText.__init__(self, parent, **kwargs)
        self.target = target
        self.hide_if_valid = hide_if_valid
        self.error_message = error_message

    def validate(self):
        """Check the target's value is valid and display the error if not."""
        is_valid = self.check()
        if not is_valid:
            self.set_msg(self.error_message)
        return is_valid

    def check(self):
        """Check if the target field's value is valid or not.

        This method must be overridden to perform check on ``self.target``.
        It should not be called directly. Use ``validate()`` instead.

        Returns:
            True if the target value is valid; otherwise False.
        """
        return True

    def set_msg(self, message=None):
        """Set an error message associated to the target.

        Args:
            message (str, optional): error message. If not set, the default
                error message will be used. The message will be translated.
        """
        if message is None:
            message = self.default_error_message

        if message is not None:
            self.SetLabel(_(message))
            self.Show()

        # red color
        self.target.SetBackgroundColour(wx.Colour(255, 148, 148))

    def reset(self):
        """Clean all error messages."""
        self.target.SetBackgroundColour(wx.NullColour)
        self.SetLabel('')
        if self.hide_if_valid:
            self.Hide()


class NotEmptyValidator(BaseValidator):
    """Ensures the fields isn't empty."""

    default_error_message = N_('This field is required.')

    def check(self):
        return not self.target.GetValue() == ''
