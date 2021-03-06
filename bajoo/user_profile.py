# -*- coding: utf-8 -*-

from copy import deepcopy
import errno
import hashlib
import logging
import os.path
import pickle
from .common.path import get_data_dir
from .common.strings import err2unicode
from .common.util import xor

_logger = logging.getLogger(__name__)


def _write_action_attr(attr, callback):
    """make a proxy of an attribute, who call a callback on write operations.

    Example:

        >>> def on_write_callback(foo_instance):
        ...     print('Write action!')
        >>> class Foo(object):
        ...   bar = 3
        ...   baz = _write_action_attr('bar', on_write_callback)
        >>> foo = Foo()
        >>> print(foo.baz)
        3
        >>> foo.baz = 5
        Write action!
        >>> print(foo.bar)
        5

    Note: the passphrase is "encrypted" with a simple xor using the email as
    key. It's not very secure, but still better than a clear passphrase.

    Args:
        attr (str): name of the proxified attribute.
    Returns:
        property: read-write property. all operations are reported on the
            "attr" attribute. When updated, the callback is called.
            If the profile file is not valid, raises an exception.
    """
    def _getter(self):
        return getattr(self, attr)

    def _setter(self, new_value):
        setattr(self, attr, new_value)
        callback(self)

    def _deleter(self):
        delattr(self, attr)
        callback(self)

    return property(_getter, _setter, _deleter)


class _InvalidUserProfile(Exception):
    """Raised when an expected user profile is not valid (can't be loaded).

    Internal used only."""


class UserProfile(object):
    """Load, save and manage all user-related data.

    an instance of UserProfile corresponds to all local data specific to a
    particular user; the user's profile. The role of UserProfile is to
    persistently stores theses data between the run of Bajoo.

    It includes the email, the last active refresh_token, the path of the root
    folder, and of the GPG folder, the fingerprint of the user's GPG key, the
    user's passphrase (if he has chosen the option "remember the passphrase"),
    and the list of the known containers and theirs status.

    A profile is stored in a file, located in the local user data directory
    (see bajoo.common.path). the file's name is XXXX.profile, where XXXX is
    the md5 hash of the user's email.

    In addition to the profile files, md5 hash of the last profile used
    (the md5 hash used in the profile file's name) is stored in a file named
    'last_profile'. At startup, this file can be used to retrieve the profile
    of the previous run of Bajoo.

    Attributes:
        email (unicode): user's email. It's also the identifier of the
            profile. It should not be modified.
        refresh_token
        root_folder_path (unicode)
        gpg_folder_path (unicode): read-only attribute.

    """

    # static property containing the email hash in the last_profile file. None
    # means we don't known.
    # It's used as a cache to avoid rewriting the file if not needed.
    _last_profile = None

    def __init__(self, user_email, _profile_file_path=None):
        """Load (or create) a new user profile.

        If there is already a profile file with the corresponding email, this
        profile file is loaded and associated to the current instance.
        If there is none, a new profile file is created. All attributes will
        be empty or None, expect for the user's email.

        In either case, all modifications of this UserProfile instance will be
        written on the file.

        Args:
            user_email (unicode)
            _profile_file_path (unicode): Internal use only! If set, load a
                profile from its file, instead of using the email value.
        """
        self.email = user_email

        self._refresh_token = None
        self._root_folder_path = None
        self._fingerprint_key = None
        self._passphrase = None

        self._containers = {}

        if _profile_file_path:
            self._load_profile(_profile_file_path)
        else:
            profile_path = self._get_profile_path()
            self._load_profile(profile_path)

    @classmethod
    def get_last_profile(cls):
        """Try to load the last profile used.

        Returns:
            UserProfile: if we've loaded a profile; otherwise None.
        """

        _logger.debug('Search last profile used ..')
        last_profile_path = os.path.join(get_data_dir(), 'last_profile')

        try:
            with open(last_profile_path, mode='r') as last_profile_file:
                email_hash = last_profile_file.read().rstrip()
        except (OSError, IOError, UnicodeError) as error:
            if getattr(error, 'errno') == errno.ENOENT:
                return None  # there is no last profile
            _logger.info('Failed to open last_profile file: %s',
                         err2unicode(error))
            return None

        UserProfile._last_profile = email_hash

        profile_file_name = u'%s.profile' % email_hash
        profile_path = os.path.join(get_data_dir(), profile_file_name)

        try:
            return UserProfile(None, _profile_file_path=profile_path)
        except _InvalidUserProfile:
            _logger.info('Failed to open the profile file "%s", '
                         'referenced in last_profile', profile_file_name)
            return None

    def _get_profile_path(self):
        """
        Returns:
            unicode: absolute path of the profile file.
        """
        # hashlib.md5 accepts only bytes data in input
        email_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        profile_path = u'%s.profile' % email_hash
        return os.path.join(get_data_dir(), profile_path)

    def _load_profile(self, file_path):
        """Load data from a profile file.

        If an error happens, it's logged, and ignored, unless the attribute
        `email` is None. So if a file is missing or corrupted, and the email
        is already set, an empty profile will be used.

        Args:
            file_path (unicode): path of the profile file.
        Raises:
            _InvalidUserProfile: if we can't find the email, and there is none
                by default.
        """
        try:
            with open(file_path, mode='rb') as profile_file:
                data = pickle.load(profile_file)

                email = data.get('email', None)
                if self.email and self.email != email:
                    _logger.warning('Corrupted %s profile file.', self.email)
                    return

                self.email = email
                self._refresh_token = data.get('refresh_token', None)
                self._root_folder_path = data.get('root_folder_path', None)
                self._fingerprint_key = data.get('fingerprint_key', None)
                encrypted_passphrase = data.get('passphrase', None)
                if encrypted_passphrase:
                    passphrase = xor(encrypted_passphrase, self.email)
                    self._passphrase = passphrase.decode('utf-8')

                self._containers = data.get('containers', {})

        except (OSError, IOError, UnicodeError, TypeError, ValueError,
                KeyError, EOFError, pickle.PickleError) as error:
            _logger.info('Failed to open last profile "%s": %s',
                         file_path, err2unicode(error))

        if self.email is None:
            raise _InvalidUserProfile()
        _logger.debug('User profile %s loaded', self.email)
        self._update_last_profile()

    def _save_data(self):
        """Save all the data into the profile file."""

        profile_file_path = self._get_profile_path()

        if self.passphrase:
            passphrase = xor(self._passphrase, self.email)
        else:
            passphrase = None
        data = {
            'email': self.email,
            'refresh_token': self._refresh_token,
            'root_folder_path': self._root_folder_path,
            'fingerprint_key': self._fingerprint_key,
            'passphrase': passphrase,
            'containers': self._containers
        }

        try:
            with open(profile_file_path, 'wb') as profile_file:
                pickle.dump(data, profile_file)
        except (OSError, IOError, UnicodeError, TypeError,
                pickle.PickleError) as error:
            _logger.info('Failed to update profile file %s: %s',
                         profile_file_path, err2unicode(error))
        else:
            _logger.debug('User profile file has been updated.')

    def _update_last_profile(self):
        email_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

        if UserProfile._last_profile != email_hash:
            last_profile_path = os.path.join(get_data_dir(), 'last_profile')
            try:
                with open(last_profile_path, mode='w+') as last_profile_file:
                    last_profile_file.write(email_hash)
            except (OSError, IOError, UnicodeError) as err:
                _logger.info('Failed to update last_profile file: %s',
                             err2unicode(err))

    refresh_token = _write_action_attr('_refresh_token', _save_data)
    root_folder_path = _write_action_attr('_root_folder_path', _save_data)
    fingerprint_key = _write_action_attr('_fingerprint_key', _save_data)
    passphrase = _write_action_attr('_passphrase', _save_data)

    @property
    def gpg_folder_path(self):
        p = u'%s-gpg' % hashlib.md5(self.email.encode('utf-8')).hexdigest()
        return os.path.join(get_data_dir(), p)

    def get_all_containers(self):
        """Returns all containers saved.

        This function is NOT thread-safe. Don't use several container-related
        methods at the same time !

        Returns:
            dict of ContainerModel: list of all containers, of the form:
                {container_id: container_model)
        """
        return deepcopy(self._containers)

    def get_container(self, id):
        """Get the container model.

        This function is NOT thread-safe. Don't use several container-related
        methods at the same time !

        Returns:
            ContainerModel: model of the container. None if it doesn't exists.
        """
        return deepcopy(self._containers.get(id, None))

    def set_container(self, id, container_model):
        """Add or update a container's data.

        This function is NOT thread-safe. Don't use several container-related
        methods at the same time !

        Args:
            container_model (ContainerModel): container's data
        """
        self._containers[id] = container_model
        self._save_data()

    def remove_container(self, id):
        """Remove a container from the list.

        This function is NOT thread-safe. Don't use several container-related
        methods at the same time !

        Returns:
            True if the container has been deleted; False if not found.
        """
        try:
            del self._containers[id]
        except KeyError:
            return False

        self._save_data()
        return True
