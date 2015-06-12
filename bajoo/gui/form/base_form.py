# -*- coding: utf-8 -*-

import wx

from ..translator import Translator


class BaseForm(wx.Window, Translator):
    """Base class for all Bajoo forms

    When the class detect an EVT_BUTTON events in automatic mode (or when
    ``disable()`` is called), it disable all fields to prevents the user to
    call the form twice.
    The previous state of each children can be restored using ``enable()``.

    Note: the EVT_BUTTON event should not be detected from the button itself:
    it will prevent the form to detect the event. Instead, it should be
    detected on the form or on the parent level.
    ie: prefers `form.Bind(wx.EVT_BUTTON, callback, button)`` to
    ``button.Bind(wx.EVT_BUTTON, callback)``

    Each child class can override the two attributes ``EVT_SUBMIT`` and
    ``SubmitEvent``. the method ``submit()`` is a quick way to submit form data
    using the defined submit event.

    Attributes:
        EVT_SUBMIT: ID of the event form (if any). Must be overridden for use.
        SubmitEvent (wx.Event subclass): Event class corresponding to
        EVT_SUBMIT.
    """

    EVT_SUBMIT = None
    SubmitEvent = None

    def __init__(self, parent, auto_disable=False, **kwargs):
        """BaseForm constructor

        Args:
            parent (wx.Window): parent
            auto_disable (boolean, optional): If set, the form will be
                automatically disabled when a wx.EVT_BUTTON occurs.
            **kwargs: arguments passed to ``wx.Window``
        """
        wx.Window.__init__(self, parent, **kwargs)
        Translator.__init__(self)

        # map Window ID <-> Previous state
        self._form_state = {}

        if auto_disable:
            self.Bind(wx.EVT_BUTTON, self._on_child_submitted)

    def _on_child_submitted(self, evt):
        self.disable()
        # TODO: add some animation to indicate a task is running.
        evt.Skip()

    def disable(self):
        """Disable children and save theirs actual states (enabled/disabled)"""
        for child in self.GetChildren():
            self._form_state[child.GetId()] = child.IsEnabled()
            child.Disable()

    def enable(self):
        """Restore all child to theirs previous states.

        Calling this method will enable/disable children in the same state
        they were before the last call of ``disable()``.
        """
        for child in self.GetChildren():
            previous_state = self._form_state.get(child.GetId(), None)
            if previous_state is not None:
                child.Enable(previous_state)

    def get_data(self):
        """Returns the content of each fields of the form.

        Returns:
            dict: a list of pair key-value. the key is the name of the child.
        """

        result = dict()
        for child in self.GetChildren():
            if hasattr(child, 'GetValue'):
                value = child.GetValue()
            elif hasattr(child, 'GetSelection'):  # wx.Choices
                value = child.GetSelection()
            else:
                continue
            result[child.GetName()] = value
        return result

    def GetValue(self):
        """Alias of ``get_data()``

        Allow to recursively call get_data() on child form.
        """
        return self.get_data()

    def submit(self, _event=None):
        """Post a SubmitEvent with form data.

        Take a dummy argument ``_event``, allowing to directly use has an event
        handler.
        """
        event = self.SubmitEvent(**self.get_data())
        wx.PostEvent(self, event)


def main():
    app = wx.App()
    win = wx.Frame(None, title='Base Form')
    app.SetTopWindow(win)

    timer = wx.Timer(win)
    win.Bind(wx.EVT_TIMER, lambda _: form.enable())

    form = BaseForm(win, auto_disable=True)
    input = wx.TextCtrl(form)
    enable_btn = wx.Button(win, label='Enable')
    disable_btn = wx.Button(form, label='No action')
    submit_btn = wx.Button(form, label='Submit')

    # Already disabled elements keep theirs state,
    # even after a call to "form.enable()"
    disabled_btn = wx.Button(form, label='Always disabled')
    disabled_btn.Disable()

    def submit_action(evt):
        print('Form data:')
        print(form.get_data())
        # The form disables itself.
        # We reactivate it when the task (the timer) is done.
        timer.Start(500, oneShot=True)

    enable_btn.Bind(wx.EVT_BUTTON, lambda _: form.enable(), enable_btn)
    win.Bind(wx.EVT_BUTTON, submit_action, submit_btn)

    form_sizer = wx.StaticBoxSizer(wx.StaticBox(form, label='form'),
                                   wx.VERTICAL)
    form_sizer.AddMany([
        (input, 0, wx.ALL, 15),
        (disable_btn, 0, wx.RIGHT | wx.LEFT | wx.BOTTOM, 15),
        (submit_btn, 0, wx.RIGHT | wx.LEFT | wx.BOTTOM, 15),
        (disabled_btn, 0, wx.RIGHT | wx.LEFT | wx.BOTTOM, 15)
    ])
    form.SetSizer(form_sizer)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(form, flag=wx.ALL, border=15)
    sizer.Add(enable_btn, flag=wx.RIGHT | wx.TOP | wx.BOTTOM, border=15)
    win.SetSizer(sizer)
    sizer.SetSizeHints(win)
    win.Show(True)
    app.MainLoop()

if __name__ == '__main__':
    main()
