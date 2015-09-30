# -*- coding: utf-8 -*-
import wx

from ...common.path import resource_filename


def get_bitmap(image_path, rescale=True, width=16, height=16):
    img = wx.Image(resource_filename('assets/images/' + image_path))

    if rescale:
        img = img.Rescale(width, height)

    return img.ConvertToBitmap()
