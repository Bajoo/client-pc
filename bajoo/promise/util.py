# -*- coding: utf-8 -*-


def is_thenable(item):
    return hasattr(item, 'then')
