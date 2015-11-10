#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gettext import NullTranslations
import os

from bajoo.common.i18n import _get_translation_instance

"""### TEST CASES ###
    locale dir exists
    lang is None
    lang is unknow
    lang exists

    TODO find a way to simulate an empty locale dir
"""


class TestI18n(object):

    def test_lang_is_None(self):
        os.environ['LANGUAGE'] = 'en'
        translation = _get_translation_instance(None)
        assert isinstance(translation, NullTranslations)
        assert translation.gettext("Read Only") == "Read Only"

    def test_lang_is_unknwon(self):
        translation = _get_translation_instance("plop")
        assert isinstance(translation, NullTranslations)
        assert translation.gettext("Read Only") == "Read Only"

    def test_lang_is_knwon_en(self):
        translation = _get_translation_instance("en")
        assert isinstance(translation, NullTranslations)
        assert translation.gettext("Read Only") == "Read Only"

    def test_lang_is_knwon_fr(self):
        translation = _get_translation_instance("fr")
        assert isinstance(translation, NullTranslations)
        assert translation.gettext("Read Only") == "Lecture seule"
