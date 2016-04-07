# -*- coding: utf-8 -*-

import logging
import wx

from ..common.i18n import _, N_
from .base_view import BaseView
from .event_promise import ensure_gui_thread

_logger = logging.getLogger(__name__)


class PassphraseWindow(wx.Dialog):
    """Passphrase prompt dialog

    Modal window who ask the user to enter his passphrase. It also offers the
    user to memorize his passphrase.

    The simplest way to use it is to call the class method `ask_passphrase()`,
    who create and destroy the window.

    If created manually, this window should be called as a modal window:

    >>> window = PassphraseWindow(False)
    >>> if window.ShowModal() == wx.ID_OK  # Can be either ID_OK or ID_CANCEL
    >>>     print(window.get_passphrase())
    >>>     print(window.allow_save_on_disk())

    Internal window elements:
     - "passphrase" is the wx.TextCtrl for the passphrase
     - "allow_save_on_disk" is a wx.CheckBox
     - "btn_ok" and "btn_cancel" are two wx.Button
     - if set "error_msg" is a wx.TextCtrl. Can be None.
    """
    def __init__(self, is_retry=False):
        wx.Dialog.__init__(self, parent=None,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        self._passphrase_input = wx.TextCtrl(self, name='passphrase',
                                             style=wx.TE_PASSWORD)
        self._allow_save_on_disk_checkbox = wx.CheckBox(
            self, name='allow_save_on_disk')
        if is_retry:
            error_message = _('Invalid passphrase!')
            wx.StaticText(self, name='error_msg', label=error_message)
        wx.Button(self, wx.ID_OK, name='btn_ok', label=_('OK'))
        wx.Button(self, wx.ID_CANCEL, name='btn_cancel', label=_('Cancel'))

        PassphraseWindowView(self)

    def get_passphrase(self):
        """
        Returns:
            str: the passphrase entered by the user.
        """
        return self._passphrase_input.GetValue()

    def allow_save_on_disk(self):
        """
        Returns:
            boolean: True if the user allow us to save his passphrase.
        """
        return self._allow_save_on_disk_checkbox.GetValue()

    @classmethod
    def ask_passphrase(cls, is_retry):
        """Ask the user to enter his passphrase, and returns it;

        As we wait for the user, this method is blocking.

        Args:
            is_retry (boolean):
        Returns:
            str, boolean: the passphrase itself (or None if the user hasn't
                responded), and a boolean indicating if the user allow us to
                remember his passphrase.
        """
        return cls._ask_passphrase(is_retry).result()

    @classmethod
    @ensure_gui_thread
    def _ask_passphrase(cls, is_retry):
        window = cls(is_retry)
        passphrase = None
        remember_passphrase = False
        if window.ShowModal() == wx.ID_OK:
            passphrase = window.get_passphrase()
            remember_passphrase = window.allow_save_on_disk()
        return passphrase, remember_passphrase


class PassphraseWindowView(BaseView):
    """View of the passphrase window."""

    def __init__(self, parent):
        BaseView.__init__(self, parent)
        self.set_frame_title(N_('Bajoo - Ask for passphrase'))

        prompt = wx.StaticText(self.window, name='_prompt_txt')

        self._set_texts()

        button_box = wx.StdDialogButtonSizer()
        button_box.SetAffirmativeButton(self.window.FindWindow("btn_ok"))
        button_box.SetCancelButton(self.window.FindWindow("btn_cancel"))
        button_box.Realize()

        self.window.FindWindow("btn_ok").SetDefault()
        error_msg = self.window.FindWindow('error_msg')

        sizer_items = []
        if error_msg:
            sizer_items.append(error_msg)
        sizer_items = sizer_items + [
            prompt,
            self.window.FindWindow('passphrase'),
            self.window.FindWindow('allow_save_on_disk'),
            None,
            button_box
        ]
        sizer = self.make_sizer(wx.VERTICAL, sizer_items, flag=wx.EXPAND)
        self.window.SetSizer(sizer)

    @BaseView.i18n_callback
    def _set_texts(self):
        message = _('Enter your Bajoo pasphrase to start the synchronization'
                    ' of your encrypted files.')
        prompt = self.window.FindWindow('_prompt_txt')
        prompt.SetLabel(message)

        checkbox = self.window.FindWindow('allow_save_on_disk')
        checkbox.SetLabel(_('Memorize the passphrase'))


def main():
    wx.App()
    win = PassphraseWindow()

    if win.ShowModal() == wx.ID_OK:
        print('OK')
    else:
        print('Action canceled')

if __name__ == '__main__':
    main()
