# -*- coding: utf-8 -*-

import gettext
import locale
from logging import getLogger
import sys

from . import config
from .path import resource_filename


_logger = getLogger(__name__)

_translation = None


def _get_translation_instance(lang):
    localedir = resource_filename('locale')
    log_str = 'Load translation from %s for language %s'

    if lang is not None:
        languages = [lang]
    elif lang is None and sys.platform == 'win32':
        languages = [locale.getdefaultlocale()[0]]
    else:
        languages = None

    try:
        tr = gettext.translation('bajoo', localedir=localedir,
                                 languages=languages)
        _logger.debug(log_str % (localedir, lang if lang else 'auto'))
        return tr
    except IOError:
        pass
    try:
        tr = gettext.translation('bajoo', localedir=localedir,
                                 languages=['en'])
        _logger.debug(log_str % (localedir, 'en (fallback)'))
        return tr
    except IOError:
        pass
    try:
        tr = gettext.translation('bajoo', languages=languages)
        _logger.debug(log_str % ('system', lang if lang else 'auto'))
        return tr
    except IOError:
        pass
    try:
        tr = gettext.translation('bajoo', languages=['en'])
        _logger.debug(log_str % ('system', 'en (fallback)'))
        return tr
    except IOError:
        _logger.error('No translation file found!')
        raise


def set_lang(lang):
    """Change the current language used for translation.

    Args:
        lang (str): the language code, like 'en', or 'fr_FR'. If None, the
            default system language will be used (if possible).
    """
    global _translation

    _translation = _get_translation_instance(lang)

    # locale_codes = [locale.normalize(lang), ''] if lang else ['']
    # for locale_code in locale_codes:
    #    try:
    #        locale.setlocale(locale.LC_ALL, locale_code)
    #        break
    #    except locale.Error:
    #        _logger.info('Failed to set locale "%s"' % locale_code,
    #                     exc_info=True)


def _(msg):
    """Translate the specified text, and return the result."""
    global _translation

    if not _translation:
        set_lang(config.get('lang'))

    try:
        if sys.version_info[0] is 3:
            return _translation.gettext(msg)
        else:
            return _translation.ugettext(msg)
    except UnicodeDecodeError:
        # gettext don't always accepts non-ascii identifiers.
        # All identifiers are ascii, so this exception happens when 'msg' is
        # a non-translated string (probably a generated string).
        return msg

available_langs = {
    None: {
        'code': None,
        'name': _('Auto'),
        'flag': ''
    },
    'en': {
        'code': 'en',
        'name': u'English',
        'flag': ''
    },
    'fr_FR': {
        'code': 'fr_FR',
        'name': u'Français (France)',
        'flag': ''
    },
    'vi_VN': {
        'code': 'vi',
        'name': u'Tiếng Việt',
        'flag': ''
    },
    'it_IT': {
        'code': 'it_IT',
        'name': u'Italian (Italy)',
        'flag': ''
    },
    'zh_CN': {
        'code': 'zh-cn',
        'name': u'Chinese (China)',
        'flag': ''
    }
}


# NOOP operation used for deferred translations.
# N_ is recognized by gettext utilities.
N_ = lambda msg: msg
