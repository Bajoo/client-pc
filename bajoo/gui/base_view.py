# -*- coding: utf-8 -*-

import wx

from ..common.path import resource_filename
from .translator import Translator
from ..common.i18n import N_


class BaseView(Translator):
    """Base class for all views.

    This class come with helper functions to configure the view.

    Class Attributes:
        LIGHT_GRAY (wx.Colour): Predefined background color.

    Attributes:
        window (wx.Window): the window element the view is in charge.
    """

    LIGHT_GRAY = wx.Colour(0xf2, 0xf2, 0xf2)

    def __init__(self, window):
        Translator.__init__(self)

        # wx.Window instance.
        self.window = window

    def set_frame_title(self, title):
        """Set the title of the wx.Frame containing this Window.

        Args:
            title (str): new frame title. The title will be translated.
        """
        frame = self.window.GetTopLevelParent()
        self.register_i18n(frame, frame.SetTitle, title)

    def make_sizer(self, direction, items, outside_border=True, flag=0,
                   proportion=0, sizer=None, border=15):
        """Recursively make sizers with border for simple cases.

        Each element given will be added to the sizer, with appropriate
        borders. Border between elements (even sub-sizer) will be merged.

        Args:
            direction: the direction of the first sizer. Can be wx.HORIZONTAL
                or wx.VERTICAL.
            items (list of wx.Window): a list of all elements to add to the
                sizer. If an item is None, a stretchable spacer is added. If
                it's another list, this function is called recursively with the
                opposite direction.
            outside_border (boolean, optional): If set to False, no outside
                border are added: Only borders between elements will be
                created.
            flag (optional): if set, additional flags who will be passed to
                each ``sizer.Add()`` call.
            proportion (optional): If set, the parameter will be passed to each
                ``sizer.Add()`` call.
            sizer (wx.Sizer, optional): If set, this empty sizer will be used,
                instead of creating a new one.
            border (integer, optional): size of the border to use
        returns:
            wx.Sizer: the top-level sizer created.
        """
        swap_direction = {
            wx.VERTICAL: wx.HORIZONTAL,
            wx.HORIZONTAL: wx.VERTICAL
        }

        if not sizer:
            sizer = wx.BoxSizer(direction)

        # the first border is implemented as a Spacer,
        # because borders of hidden elements don't appears.
        if outside_border:
            sizer.AddSpacer(border)

        for (index, item) in enumerate(items):
            if item is None:
                sizer.AddStretchSpacer()
                continue

            flags = 0
            if isinstance(item, list):
                item = self.make_sizer(swap_direction[direction], item,
                                       outside_border=False)

            if isinstance(item, wx.Sizer):
                flags |= wx.EXPAND

            # Compute flag for merging common border.
            if outside_border:
                if direction is wx.VERTICAL:
                    flags |= wx.LEFT | wx.RIGHT
                else:
                    flags |= wx.TOP | wx.BOTTOM
            if len(items) - 1 is not index:
                if direction is wx.VERTICAL:
                    flags |= wx.BOTTOM
                else:
                    flags |= wx.RIGHT

            flags |= flag
            sizer.Add(item, border=border, flag=flags, proportion=proportion)

        # last border
        if outside_border:
            sizer.AddSpacer(border)

        return sizer

    def create_settings_button_box(self, parent):
        """Create a common box with 3 buttons: ok, cancel, apply"""
        btn_ok = wx.Button(parent, wx.ID_OK, name='btn_ok')
        btn_cancel = wx.Button(parent, wx.ID_CANCEL, name='btn_cancel')
        btn_apply = wx.Button(parent, wx.ID_APPLY, name='btn_apply')

        self.register_many_i18n('SetLabel', {
            btn_cancel: N_('Cancel'),
            btn_ok: N_('OK'),
            btn_apply: N_('Apply')
        })

        # Buttons box
        button_box = wx.StdDialogButtonSizer()

        button_box.SetAffirmativeButton(btn_ok)
        button_box.SetCancelButton(btn_cancel)
        button_box.AddButton(btn_apply)

        # Layout the button box
        button_box.Realize()

        return button_box

    def set_icon(self):
        """Set the standard Bajoo favicon to the window.

        Note that the window must be an instance of wx.Frame.
        """
        icon_path = resource_filename('assets/window_icon.png')
        icon = wx.Icon(icon_path)
        self.window.SetIcon(icon)
