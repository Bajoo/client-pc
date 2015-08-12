# -*- coding: utf-8 -*-

import logging

import wx
import wx.dataview as dv
from wx.lib.newevent import NewCommandEvent

from ..translator import Translator
from ..event_future import ensure_gui_thread
from ..base_view import BaseView
from .base_form import BaseForm
from ..validator import EmailValidator
from ...common.i18n import N_
from ...common.path import resource_filename

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
    RemoveMemberEvent, EVT_REMOVE_MEMBER = NewCommandEvent()

    fields = ['user_email', 'permission']

    ADD_ICON = None

    def __init__(self, parent, auto_disable=False, **kwargs):
        BaseForm.__init__(self, parent, auto_disable, **kwargs)
        self._init_icons()
        self._view = MembersShareView(self)
        self.validators = self._view.get_validators()
        self._members = []

        self.Bind(wx.EVT_BUTTON, self.submit, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self._btn_remove_user_clicked,
                  id=wx.ID_DELETE)
        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self._on_select_member)

    def _init_icons(self):
        if not MembersShareForm.ADD_ICON:
            MembersShareForm.ADD_ICON = wx.Image(resource_filename(
                'assets/images/add.png')) \
                .ConvertToBitmap()

    def load_members(self, members):
        self._members = members
        self._view.load_members_view(members)

    def add_member(self, member):
        self._members.append(member)
        self._view.add_member_view(member)

    def remove_member(self, member):
        self._members.remove(member)
        self._view.remove_member_view(member)

    def on_add_member(self, member):
        self._view.on_add_member(member)

    def get_data(self):
        data = BaseForm.get_data(self)
        cmb_permission = self.FindWindow('permission')
        data['permission'] = cmb_permission.GetClientData(
            cmb_permission.GetSelection())

        return data

    def _on_select_member(self, _event):
        row = self._view._members_list_view.GetSelectedRow()
        txt_user_email = self.FindWindow('user_email')
        btn_remove_user = self.FindWindow('btn_remove_user')

        if row == wx.NOT_FOUND:
            txt_user_email.SetValue('')
            btn_remove_user.Disable()
        else:
            # TODO: check admin permission
            email = self._view._members_list_view.GetValue(row, 0)
            txt_user_email.SetValue(email)
            btn_remove_user.Enable()

    def _btn_remove_user_clicked(self, event):
        # TODO: confirmation
        remove_event = MembersShareForm.RemoveMemberEvent(self.GetId())
        remove_event.email = self.FindWindow('user_email').GetValue()

        wx.PostEvent(self, remove_event)


class MembersShareView(BaseView):
    def __init__(self, members_share_form):
        BaseView.__init__(self, members_share_form)

        self._data = None
        members_list_view = dv.DataViewListCtrl(members_share_form)
        user_col = members_list_view.AppendTextColumn('', width=200)
        permission_col = members_list_view.AppendTextColumn('', width=100)
        actions_col = members_list_view.AppendTextColumn('', width=50)
        members_list_view.SetMinSize((400, 100))
        self._members_list_view = members_list_view
        self.register_many_i18n('SetTitle', {
            user_col: N_('User'),
            permission_col: N_('Permission'),
            actions_col: N_('-')
        })

        txt_user_email = wx.TextCtrl(
            members_share_form, name='user_email')
        txt_user_email.SetHint(N_('Email'))
        email_error = EmailValidator(
            members_share_form, name='email_error', target=txt_user_email)
        self._email_error = email_error

        cmb_permission = wx.ComboBox(
            members_share_form, name='permission',
            style=wx.CB_READONLY, value=N_('Admin'))
        cmb_permission.Append(N_('Admin'), 'ADMIN')
        cmb_permission.Append(N_('Read Write'), 'READ_WRITE')
        cmb_permission.Append(N_('Read Only'), 'READ_ONLY')
        cmb_permission.SetSelection(0)
        self._cmb_permission = cmb_permission

        btn_add_user = wx.BitmapButton(
            members_share_form, id=wx.ID_APPLY,
            bitmap=MembersShareForm.ADD_ICON,
            name='btn_add_user')
        btn_remove_user = wx.Button(
            members_share_form, id=wx.ID_DELETE,
            name='btn_remove_user', label=N_('Remove'))
        btn_remove_user.Disable()

        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        user_sizer.Add(txt_user_email, proportion=2,
                       flag=wx.EXPAND | wx.RIGHT, border=15)
        user_sizer.Add(email_error)
        user_sizer.Add(cmb_permission, proportion=1,
                       flag=wx.EXPAND | wx.RIGHT, border=15)
        user_sizer.Add(btn_add_user, proportion=0)
        user_sizer.Add(btn_remove_user, proportion=0)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(members_list_view,
                       flag=wx.EXPAND,
                       proportion=1, border=0)
        main_sizer.Add(user_sizer,
                       flag=wx.EXPAND | wx.TOP,
                       proportion=0, border=15)
        members_share_form.SetSizer(main_sizer)

    def notify_lang_change(self):
        Translator.notify_lang_change(self)
        self.load_members_view()
        self._cmb_permission.SetString(0, N_('Admin'))
        self._cmb_permission.SetString(1, N_('Read Write'))
        self._cmb_permission.SetString(2, N_('Read Only'))

    @ensure_gui_thread
    def load_members_view(self, members=None):
        if members is None:
            members = self._data
        else:
            self._data = members

        self._members_list_view.DeleteAllItems()

        for member in members:
            self.add_member_view(member)

    def add_member_view(self, member):
        email = member.get('user', '<unknown>')
        permission = N_('Read Only')

        if member.get('admin'):
            permission = N_('Admin')
        elif member.get('write'):
            permission = N_('Read Write')

        # TODO: add delete button
        delete = 'Delete'
        self._members_list_view.AppendItem([email, permission, delete])

    def on_add_member(self, member):
        _logger.debug("on_share_member_added")
        if self._data:
            for index, member_data in enumerate(self._data):
                _logger.debug('%s vs %s', member_data.get(u'user'), member.get(u'user'))
                if member_data.get(u'user') == member.get(u'user'):
                    self._data.remove(member_data)
                    self._data.insert(index, member)

                    self.load_members_view()
                    return

        self.add_member_view(member)

    def remove_member_view(self, member):
        pass

    def get_validators(self):
        return [self._email_error]


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
