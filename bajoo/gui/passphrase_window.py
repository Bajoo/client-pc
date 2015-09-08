# -*- coding: utf-8 -*-

import logging

import wx

from ..common.i18n import _

_logger = logging.getLogger(__name__)


class PassphraseWindow(wx.TextEntryDialog):

    def __init__(self, is_retry=False):
        message = _('Enter your Bajoo pasphrase to start the synchronization'
                    ' of your encrypted files.')
        if is_retry:
            message = _('Invalid passphrase !') + '\n\n' + message
        wx.TextEntryDialog.__init__(
            self, parent=None, message=message,
            style=wx.TextEntryDialogStyle | wx.TE_PASSWORD)
        self.SetTitle(_('Bajoo - Ask for passphrase'))
