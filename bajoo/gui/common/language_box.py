# -*- coding: utf-8 -*-
import wx
from wx.lib.newevent import NewCommandEvent

from ...common.i18n import available_langs


class LanguageBox(wx.ComboBox):
    """
    A language combo box which allows user to set application's language.
    If option 'Auto' is chosen, the system's default language will be used.
    """

    LanguageEvent, EVT_LANG = NewCommandEvent()

    def __init__(self, *args, **kwargs):
        """
        Args:
            current_lang_code: the currently used language code,
                by default the system language.
            Other arguments are like in wx.ComboBox.__init__()
        """
        if not 'style' in kwargs:
            kwargs['style'] = wx.CB_READONLY

        current_lang_code = kwargs.pop('current_lang_code', None)
        wx.ComboBox.__init__(self, *args, **kwargs)
        self._langs = available_langs.items()

        for lang_code, lang_info in self._langs:
            self.Append(lang_info.get('name', ''), lang_code)

        self.select_language(current_lang_code)
        self.Bind(wx.EVT_COMBOBOX, self._on_selection_changed)

    def select_language(self, lang_code):
        """
        Select a language option according to the language code.
        """
        for i in range(self.GetCount()):
            if lang_code == self.GetClientData(i):
                self.Select(i)

        return

    def _on_selection_changed(self, event):
        lang_code = self.GetClientData(self.GetSelection())
        wx.PostEvent(self, LanguageBox.LanguageEvent(
            self.GetId(), lang=lang_code))


def main():
    app = wx.App()
    win = wx.Frame(None)

    language_box = LanguageBox(win, current_lang_code='fr_FR')

    def _lang_selection_changed(event):
        print('Selected Language: ', event.lang)

    win.Bind(LanguageBox.EVT_LANG, _lang_selection_changed)

    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(language_box, 0, wx.EXPAND, 0)
    sizer.SetSizeHints(win)
    win.SetSizer(sizer)

    win.Show(True)
    app.MainLoop()


if __name__ == '__main__':
    main()
