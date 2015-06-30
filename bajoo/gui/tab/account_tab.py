# -*- coding: utf-8 -*-

import wx

from ...common.i18n import N_
from ..base_view import BaseView


class AccountTab(wx.Panel):
    """
    Account settings tab in the main window, which allows user to:
    * view account information like email, quota
    * change password
    * change offer plan
    * reset encryption passphrase
    * disconnect
    """

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self._view = AccountView(self)


class AccountView(BaseView):
    """View of the account screen"""

    def __init__(self, account_screen):
        BaseView.__init__(self, account_screen)
