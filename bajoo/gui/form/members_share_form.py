# -*- coding: utf-8 -*-

import logging

import wx
import wx.dataview as dv
from wx.lib.newevent import NewCommandEvent

from ..base_view import BaseView
from .base_form import BaseForm
from ...common.i18n import N_

_logger = logging.getLogger(__name__)


class MembersShareForm(BaseForm):
    """
    A form which allows users to manager user accesses to a team share.
    This user must be an administrator of the share to use this form.
    The form contains a list of users their permissions on this share.
    The admin can share it with another user, or can modify the current
    permission of a user, or kick he/she out of the shared folder.
    """
    SubmitEvent, EVT_SUBMIT = NewCommandEvent()
    fields = ['user_email', 'permission']

    def __init__(self, parent):
        BaseForm.__init__(self, parent)
        self._view = MembersShareView(self)
        self._members = []
        self.Bind(wx.EVT_BUTTON, self.submit,
                  self.FindWindowById(wx.ID_APPLY))

    def load_members(self, members):
        self._members = members
        self._view.load_members_view(members)

    def add_member(self, member):
        self._members.append(member)
        self._view.add_member_view(member)

    def remove_member(self, member):
        self._members.remove(member)
        self._view.remove_member_view(member)


class MembersShareView(BaseView):
    def __init__(self, members_share_form):
        BaseView.__init__(self, members_share_form)

        members_list_view = dv.DataViewListCtrl(members_share_form)
        members_list_view.AppendTextColumn(N_('User'), width=200)
        members_list_view.AppendTextColumn(N_('Permission'), width=100)
        members_list_view.AppendTextColumn(N_(''), width=50)
        members_list_view.SetMinSize((400, 100))

        txt_user_email = wx.TextCtrl(
            members_share_form, name='user_email')
        txt_user_email.SetHint(N_('Email'))

        cmb_permission = wx.ComboBox(
            members_share_form, name='permission',
            style=wx.CB_READONLY, value=N_('Admin'))
        cmb_permission.Append(N_('Admin'), 'ADMIN')
        cmb_permission.Append(N_('Read Write'), 'READ_WRITE')
        cmb_permission.Append(N_('Read Only'), 'READ_ONLY')
        cmb_permission.SetSelection(0)

        btn_add_user = wx.Button(
            members_share_form, label=N_('Add'), name='btn_add_user', )

        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        user_sizer.Add(txt_user_email, proportion=2,
                       flag=wx.EXPAND | wx.RIGHT, border=15)
        user_sizer.Add(cmb_permission, proportion=1,
                       flag=wx.EXPAND | wx.RIGHT, border=15)
        user_sizer.Add(btn_add_user, proportion=0)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(members_list_view,
                       flag=wx.EXPAND,
                       proportion=1, border=0)
        main_sizer.Add(user_sizer,
                       flag=wx.EXPAND | wx.TOP,
                       proportion=0, border=15)
        members_share_form.SetSizer(main_sizer)

    def load_members_view(self, members):
        pass

    def add_member_view(self, member):
        pass

    def remove_member_view(self, member):
        pass


def main():
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    app = wx.App()
    win = wx.Frame(None, title='Members Share Form')
    form = MembersShareForm(win)
    app.SetTopWindow(win)

    def _on_member_submitted(event):
        _logger.debug('Member submitted: %s -> %s',
                      event.user_email, event.permission)

    win.Bind(MembersShareForm.EVT_SUBMIT, _on_member_submitted)
    win.Show(True)

    from ...api import Session, Container

    def _on_session_loaded(session):
        return Container.find(session, '0a2521d8edb44828a1a91e44dd4aa410')

    def _on_share_found(share):
        return share.list_members()

    def _on_get_members(members):
        _logger.debug(members)
        form.load_members(members)

    Session.create_session(
        'stran+21@bajoo.fr', 'stran+21@bajoo.fr') \
        .then(_on_session_loaded) \
        .then(_on_share_found) \
        .then(_on_get_members)

    app.MainLoop()


if __name__ == '__main__':
    main()
