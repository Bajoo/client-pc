# -*- coding: utf-8 -*-

import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import N_
from ...common.path import default_root_folder
from ..base_view import BaseView
from ..form import BaseForm
from ..validator import BaseValidator
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

    fields = ['passphrase', 'confirmation', 'no_passphrase', 'bajoo_folder',
              'allow_save_on_disk']

    def __init__(self, parent):
        BaseForm.__init__(self, parent, auto_disable=True)
        self._view = SetupConfigScreenView(self)
        self.add_i18n_child(self._view)

        self.validators = [
            self.FindWindow('gpg_error'),
            self.FindWindow('root_folder_error'),
            self.FindWindow('passphrase_validator'),
            self.FindWindow('confirmation_validator'),
        ]

        self.FindWindow('bajoo_folder').SetPath(default_root_folder())

        self.Bind(wx.EVT_CHECKBOX, self.apply_field_constraints)

        self.Bind(wx.EVT_BUTTON, self.submit,
                  source=self.FindWindow('validate_btn'))

    def apply_field_constraints(self, _event=None):
        use_passphrase = not self.FindWindow('no_passphrase').IsChecked()
        self.FindWindow('passphrase').Enable(use_passphrase)
        self.FindWindow('confirmation').Enable(use_passphrase)
        self.FindWindow('passphrase_validator').reset()
        self.FindWindow('confirmation_validator').reset()
        self.FindWindow('allow_save_on_disk').Enable(use_passphrase)

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
            root_folder_error_txt.set_msg(root_folder_error)
        self.FindWindow('bajoo_folder_section').Show(folder_setting)
        self.apply_field_constraints()

        gpg_error_txt = self.FindWindow('gpg_error')
        if gpg_error:
            gpg_error_txt.set_msg(gpg_error)
        self.FindWindow('encryption_form').Show(key_setting)
        self.FindWindow('encryption_section').Show(
            bool(key_setting or gpg_error))

        self.enable()

        self._reset_validators(key_setting, folder_setting)
        self.GetTopLevelParent().Layout()

    def _reset_validators(self, key_setting, folder_setting):
        # Reset validators
        self.validators = []

        if key_setting:
            self.validators.append(self.FindWindow('gpg_error'))
            self.validators.append(self.FindWindow('passphrase_validator'))
            self.validators.append(self.FindWindow('confirmation_validator'))

        if folder_setting:
            self.validators.append(self.FindWindow('root_folder_error'))


class SetupConfigScreenView(BaseView):
    def __init__(self, screen):
        BaseView.__init__(self, screen)

        self.set_frame_title(N_('Bajoo - Configuration'))

        validate_btn = wx.Button(self.window, id=wx.ID_OK, name='validate_btn')

        encryption_section = wx.StaticBox(self.window,
                                          name='encryption_section')
        gpg_error = BaseValidator(encryption_section, hide_if_valid=True,
                                  name='gpg_error')
        encryption_form = wx.Window(encryption_section,
                                    name='encryption_form')

        encryption_txt = wx.StaticText(encryption_form)
        passphrase = wx.TextCtrl(encryption_form, name='passphrase',
                                 style=wx.TE_PASSWORD)
        passphrase_validator = MinLengthValidator(
            encryption_form, name='passphrase_validator',
            target=passphrase, min_length=8)
        confirmation = wx.TextCtrl(encryption_form, name='confirmation',
                                   style=wx.TE_PASSWORD)
        confirmation_validator = ConfirmPasswordValidator(
            encryption_form, name='confirmation_validator',
            target=confirmation, ref=passphrase)
        no_passphrase = wx.CheckBox(encryption_form, name='no_passphrase')

        allow_save_on_disk_checkbox = wx.CheckBox(
            encryption_form, name='allow_save_on_disk')

        bajoo_folder_section = wx.StaticBox(self.window,
                                            name='bajoo_folder_section')
        root_folder_error = BaseValidator(bajoo_folder_section,
                                          hide_if_valid=True,
                                          name='root_folder_error')

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
            allow_save_on_disk_checkbox: N_('Memorize the passphrase'),
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
        self.make_sizer(wx.VERTICAL, [gpg_error, encryption_form],
                        sizer=encryption_sizer, flag=wx.EXPAND)
        encryption_form_sizer = self.make_sizer(wx.VERTICAL, [
            encryption_txt, passphrase_sizer, confirmation_sizer,
            allow_save_on_disk_checkbox, no_passphrase
        ], flag=wx.EXPAND, outside_border=False)
        encryption_form.SetSizer(encryption_form_sizer)

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
