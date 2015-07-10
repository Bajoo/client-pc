# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_, _
from ...common.path import default_root_folder
from ..base_view import BaseView
from ..form import BaseForm
from ..validator import ConfirmPasswordValidator, MinLengthValidator


class SetupConfigScreen(BaseForm):
    """Ask the user about settings needed to start the sync.

    Attributes:
        EVT_ACTIVATION_DONE (Event Id): event emitted when the user indicates
            to have activated his account.
        EVT_ACTIVATION_DELAYED (Event Id): event emitted when the user
            indicates he will not activate his account soon.
    """

    SubmitEvent, EVT_SUBMIT = NewCommandEvent()

    fields = ['passphrase', 'confirmation', 'no_passphrase', 'bajoo_folder']

    def __init__(self, parent):
        BaseForm.__init__(self, parent, auto_disable=True)
        self._view = SetupConfigScreenView(self)

        self.validators = [
            self.FindWindow('passphrase_validator'),
            self.FindWindow('confirmation_validator'),
        ]

        self.FindWindow('bajoo_folder').SetPath(default_root_folder())

        self.Bind(wx.EVT_CHECKBOX, self.apply_field_constraints)

        self.Bind(wx.EVT_BUTTON, self.submit,
                  source=self.FindWindow('validate_btn'))

    def apply_field_constraints(self, _event):
        use_passphrase = not self.FindWindow('no_passphrase').IsChecked()
        self.FindWindow('passphrase').Enable(use_passphrase)
        self.FindWindow('confirmation').Enable(use_passphrase)
        self.FindWindow('passphrase_validator').reset()
        self.FindWindow('confirmation_validator').reset()

    def get_data(self):
        data = BaseForm.get_data(self)

        if data['no_passphrase']:
            data['passphrase'] = None
        del data['no_passphrase']
        del data['confirmation']
        return data

    def reset_form(self, folder_setting, key_setting, root_folder_error=None,
                   gpg_error=None):

        root_folder_error_txt = self.FindWindow('root_folder_error')
        if root_folder_error:
            root_folder_error_txt.SetLabel(_(root_folder_error))
            root_folder_error_txt.Show()
        else:
            root_folder_error_txt.Hide()
        self.FindWindow('encryption_section').Show(key_setting)
        self.FindWindow('passphrase').Enable(key_setting)
        self.FindWindow('confirmation').Enable(key_setting)

        gpg_error_txt = self.FindWindow('gpg_error')
        if gpg_error:
            gpg_error_txt.SetLabel(_(gpg_error))
            gpg_error_txt.Show()
        else:
            gpg_error_txt.Hide()
        self.FindWindow('bajoo_folder_section').Show(folder_setting)
        self.enable()

        self.GetTopLevelParent().Layout()


class SetupConfigScreenView(BaseView):

    def __init__(self, screen):
        BaseView.__init__(self, screen)

        self.set_frame_title(N_('Bajoo - Configuration'))

        validate_btn = wx.Button(self.window, id=wx.ID_OK, name='validate_btn')

        encryption_section = wx.StaticBox(self.window,
                                          name='encryption_section')
        gpg_error = wx.StaticText(encryption_section, name='gpg_error')
        gpg_error.Show(False)

        encryption_txt = wx.StaticText(encryption_section)
        passphrase = wx.TextCtrl(encryption_section, name='passphrase',
                                 style=wx.TE_PASSWORD)
        passphrase_validator = MinLengthValidator(
            encryption_section, name='passphrase_validator',
            target=passphrase, min_length=8)
        confirmation = wx.TextCtrl(encryption_section, name='confirmation',
                                   style=wx.TE_PASSWORD)
        confirmation_validator = ConfirmPasswordValidator(
            encryption_section, name='confirmation_validator',
            target=confirmation, ref=passphrase)
        no_passphrase = wx.CheckBox(encryption_section, name='no_passphrase')

        bajoo_folder_section = wx.StaticBox(self.window,
                                            name='bajoo_folder_section')
        root_folder_error = wx.StaticText(bajoo_folder_section,
                                          name='root_folder_error')
        root_folder_error.Show(False)

        bajoo_folder_label = wx.StaticText(bajoo_folder_section)
        folder_picker = wx.DirPickerCtrl(bajoo_folder_section,
                                         name='bajoo_folder',
                                         style=wx.DIRP_USE_TEXTCTRL)

        self.register_many_i18n('SetLabel', {
            encryption_section: N_('Encryption'),
            encryption_txt: N_("Your passphrase is known only by yourself. "
                               "It's used to encrypt your data.\n"
                               "It should contains at least 8 characters."
                               "You can use a real phrase to memorize it more "
                               "easily (ex: MyBajooAccount)."),
            no_passphrase: N_("Don't use encryption passphrase"),
            bajoo_folder_section: N_('Root folder Bajoo'),
            bajoo_folder_label: N_('Your Bajoo shares will be deposit here:'),
            validate_btn: N_('Validate')
        })

        self.register_many_i18n('SetHint', {
            passphrase: N_('Passphrase'),
            confirmation: N_('passphrase confirmation')
        })

        passphrase_sizer = self.make_sizer(wx.HORIZONTAL, [
            passphrase, passphrase_validator
        ], outside_border=False, flag=wx.EXPAND, proportion=1)
        passphrase_sizer.GetItem(passphrase).Proportion = 2
        confirmation_sizer = self.make_sizer(wx.HORIZONTAL, [
            confirmation, confirmation_validator
        ], outside_border=False, flag=wx.EXPAND, proportion=1)
        confirmation_sizer.GetItem(confirmation).Proportion = 2

        encryption_sizer = wx.StaticBoxSizer(encryption_section, wx.VERTICAL)
        self.make_sizer(wx.VERTICAL, [
            gpg_error, encryption_txt, passphrase_sizer, confirmation_sizer,
            no_passphrase
        ], sizer=encryption_sizer, flag=wx.EXPAND)

        bajoo_folder_sizer = wx.StaticBoxSizer(bajoo_folder_section,
                                               wx.VERTICAL)

        self.make_sizer(wx.VERTICAL, [
            root_folder_error, [bajoo_folder_label, folder_picker]
        ], flag=wx.EXPAND, sizer=bajoo_folder_sizer)
        bajoo_folder_sizer.GetItem(folder_picker,
                                   recursive=True).Proportion = 1

        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(validate_btn)
        btn_sizer.Realize()

        sizer = self.make_sizer(wx.VERTICAL, [
            encryption_sizer, bajoo_folder_sizer, None, btn_sizer
        ], flag=wx.EXPAND)
        self.window.SetSizer(sizer)


def main():
    app = wx.App()
    win = wx.Frame(None)
    app.SetTopWindow(win)
    screen = SetupConfigScreen(win)
    screen.GetSizer().SetSizeHints(win)
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
