# -*- coding: utf-8 -*-

from logging import getLogger
import wx

from ..translator import Translator

_logger = getLogger(__name__)


class BaseForm(wx.Window, Translator):
    """Base class for all Bajoo forms

    A form is a window containing user controls, like buttons, input fields and
    choice lists. It provides useful behavior to get and set data of all these
    objects.

    This class use mainly the ``name`` property to access to its children. All
    field components should have a unique name.

    The field children (child used as user input) are defined by theirs names
    and should be listed in the ``fields`` attributes. If not, all children
    will be considered as a field component, unless its name start with an
    underscore.

    The methods ``get_data()`` and ``set_data()`` are here to get and set
    values of all fields of the form.


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
            SubmitEvent (wx.CommandEvent subclass): Event class corresponding
            to EVT_SUBMIT.
        msg_windows (list of str): list of wx.Window names who should be erased
            after each submit. Typical use are validator and error messages.
        fields (list of str): If defined in subclass, list of child's name
            considered as form fields. If not set, all
        validators (list of Validator): vadidator that will be checked during
            submit.
    """

    EVT_SUBMIT = None
    SubmitEvent = None

    fields = None

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

        self.validators = []

        self.auto_disable = auto_disable

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
        if self.fields:
            children = filter(None, [self.FindWindowByName(name)
                                     for name in self.fields])
        else:
            children = [c for c in self.GetChildren()
                        if not c.GetName().startswith('_')]

        for child in children:
            if child.GetName().startswith('_'):
                continue

            if hasattr(child, 'GetValue'):
                value = child.GetValue()
            elif hasattr(child, 'GetSelection'):  # wx.Choices
                value = child.GetSelection()
            else:
                continue
            result[child.GetName()] = value
        return result

    def set_data(self, **data):
        """Set the content of form fields.

        Args:
            **data: list of pairs key/value corresponding to field's name and
                associated value to set.
        """
        for (name, value) in data.items():
            if self.fields and name not in self.fields:
                _logger.warning('Try to set value to non-valid field %s in %s'
                                % (name, self))
                continue
            child = self.FindWindowByName(name)
            if not child:
                _logger.warning('Try to set value to unknown field %s in %s'
                                % (name, self))
                continue

            if hasattr(child, 'SetValue'):
                child.SetValue(value)
            elif hasattr(child, 'SetSelection'):  # wx.Choices
                child.SetSelection(value)

    def GetValue(self):
        """Alias of ``get_data()``

        Allow to recursively call get_data() on child form.
        """
        return self.get_data()

    def _apply_validation(self):
        """Call all validator to check validity of user input."""
        result = True
        for v in self.validators:
            v.reset()
            if not v.validate():
                if result:
                    # first element to fail
                    v.target.SetFocus()
                result = False
        return result

    def submit(self, event=None):
        """Post a SubmitEvent with form data.

        Before sending the event, the child's validators will be checked, and
        the submit aborted if there is an error.

        If the ``auto_disable`` option is set, the form will be disabled.

        Take a dummy argument ``_event``, allowing to directly use has an event
        handler.
        """
        if not self._apply_validation():
            # Validators may have updated windows, so we need to update layout.
            self.GetTopLevelParent().Layout()
            return

        if self.auto_disable:
            self.disable()
        self.GetTopLevelParent().Layout()
        submit_event = self.SubmitEvent(self.GetId(), **self.get_data())
        wx.PostEvent(self, submit_event)


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
