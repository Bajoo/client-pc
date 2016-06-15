# -*- coding: utf-8 -*-

import hashlib
from imp import reload
import os
import random
import string
import pytest
import bajoo.common.path
import bajoo.user_profile


class TestUserProfile(object):

    @pytest.fixture()
    def user_profile(self, monkeypatch, tmpdir):
        monkeypatch.setattr(bajoo.common.path, 'get_data_dir',
                            lambda: str(tmpdir))
        reload(bajoo.user_profile)
        return bajoo.user_profile.UserProfile

    def get_email_address(self):
        random_id = ''.join(random.choice(string.ascii_letters + string.digits)
                            for _ in range(6))
        return 'random-%s@bajoo.fr' % random_id

    def _get_md5_checksum(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def test_create_new_profile(self, user_profile, tmpdir):
        email = self.get_email_address()
        profile = user_profile(email)
        # Note: thet file is created only when an attribute is set.
        profile.refresh_token = 'Value1'

        assert profile.email is email

        m = hashlib.md5()
        m.update(email.encode('utf-8'))
        profile_path = os.path.join(str(tmpdir), '%s.profile' % m.hexdigest())
        print(profile_path, os.path.exists(profile_path))
        assert os.path.exists(profile_path)

    def test_getter_setters(self, user_profile, tmpdir):
        email = self.get_email_address()
        profile = user_profile(email)
        profile.refresh_token = 'XXX'
        assert profile.refresh_token is 'XXX'

        m = hashlib.md5()
        m.update(email.encode('utf-8'))
        profile_path = os.path.join(str(tmpdir), '%s.profile' % m.hexdigest())
        checksum = self._get_md5_checksum(profile_path)
        profile.refresh_token = 'YYY'
        # File should have changed.
        assert checksum is not self._get_md5_checksum(profile_path)

    def test_load_existing_profile(self, user_profile):
        email = self.get_email_address()
        profile = user_profile(email)
        profile.refresh_token = 'Value1'
        profile.root_folder_path = 'Value2'
        profile.fingerprint_key = 'Value3'
        profile.passphrase = 'Value4'

        # reload
        profile = user_profile(email)
        assert profile.email == email
        assert profile.refresh_token == 'Value1'
        assert profile.root_folder_path == 'Value2'
        assert profile.fingerprint_key == 'Value3'
        assert profile.passphrase == 'Value4'

    def test_unicode_values(self, user_profile):
        email = self.get_email_address()
        value = u'❤ ☀ ☆ '
        profile = user_profile(email)
        profile.root_folder_path = value
        assert profile.root_folder_path == value

        profile = user_profile(email)  # reload
        assert profile.root_folder_path == value

    def test_last_profile_is_null(self, user_profile):
        assert user_profile.get_last_profile() is None

    def test_load_last_profile(self, user_profile):
        email = self.get_email_address()
        p1 = user_profile(email)
        p1.refresh_token = 'R1'
        email = self.get_email_address()
        p2 = user_profile(email)
        p2.refresh_token = 'R2'
        profile = user_profile.get_last_profile()
        assert isinstance(profile, user_profile)
        assert profile.email == email
        assert profile.refresh_token == 'R2'
