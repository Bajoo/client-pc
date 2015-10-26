# -*- coding: utf-8 -*-

import logging
from threading import Lock

from ..promise import Promise, reduce_coroutine
from .. import encryption
from ..network.errors import HTTPNotFoundError
from . import User


_logger = logging.getLogger(__name__)


class Container(object):
    """
    Represent a Bajoo container, which can be the MyBajoo folder,
    a TeamShare or a PublicShare.
    This should always be used as an abstract class.

    Static Attributes:
        passphrase_callback (callable): callback passed to
            `encryption.decrypt()` for asking the passphrase.
    Attributes:
        id: container id
        name: container name
        is_encrypted (boolean): If True, the container has a '.key' item, and
            all other files are encrypted by this key.
        error (Exception): if set, the container has failed during the key
            loading. It can be either a network error or an encryption error.
            this exception has an attribute 'container_id'.
    """

    passphrase_callback = None

    def __init__(self, session, container_id, name, encrypted=True):
        """
        Init a new Container object with user session, container's id & name.

        Args:
            session (bajoo.api.session.Session): user session
            container_id (str): container's id
            name (str): container's name
            encrypted (boolean, optional): Determine if the container is
                encrypted or not.
        """
        self._session = session
        self.id = container_id
        self.name = name
        self.is_encrypted = encrypted
        self.error = None

        self._encryption_key = None

        # Lock acquired when we need to generate the key. If the lock is
        # blocking, there will be a new key when releasing.
        self._key_lock = Lock()

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        s = "<Container '%s' (id=%s, encrypted=%s)>" % \
            (self.name, self.id, self.is_encrypted)
        if not isinstance(s, str):
            # Python 2 with type unicode.
            s = s.encode('utf-8')
        return s

    @reduce_coroutine()
    def _get_encryption_key(self):
        """get the encryption key and returns it.

        If the key is not present in local, it will be downloaded.

        Returns:
            Promise<AsyncKey>: container key
        """

        with self._key_lock:
            if self._encryption_key:
                yield self._encryption_key
                return

            _logger.debug('Download key of container #%s ...' % self.id)
            key_url = '/storages/%s/.key' % self.id

            try:
                result = yield self._session.download_storage_file('GET',
                                                                   key_url)
            except HTTPNotFoundError:
                _logger.debug('Container key not found (404)')
                yield self._generate_key(lock_acquired=True)
                yield self._encryption_key
                return
            except Exception as error:
                error.container_id = self.id
                self.error = error
                raise error

            enc_key_content = result.get('content')
            _logger.debug('Key of container #%s downloaded' % self.id)
            key_content = yield encryption.decrypt(
                enc_key_content,
                passphrase_callback=Container.passphrase_callback)

            key = encryption.AsymmetricKey.load(key_content)
            self._encryption_key = key
            yield key
            return

    @reduce_coroutine()
    def _encrypt_and_upload_key(self, key, use_local_members=False):
        """
        Args:
            use_local_members (boolean):
                True to use its own member array,
                False to send API request to download the member list.
        Returns:
            Promise
        """
        self._encryption_key = key
        key_content = key.export(secret=True)

        # TODO: code smell: we shouldn't use methods of child classes.
        if hasattr(self, 'list_members'):
            if use_local_members:
                members = self.members or []
            else:
                members = yield self.list_members()
            recipients = yield Promise.all(
                [User(member['user'], self._session).get_public_key()
                 for member in members])
        else:
            user = yield User.load(self._session)
            yield user.get_user_info()
            key = yield user.get_public_key()
            recipients = [key]

        enc_key_content = yield encryption.encrypt(key_content, recipients)

        # Upload key
        key_url = '/storages/%s/.key' % self.id
        _logger.debug('Key for container #%s generated.' % self.id)
        yield self._session.send_storage_request(
            'PUT', key_url, data=enc_key_content)
        return

    @reduce_coroutine()
    def _generate_key(self, lock_acquired=False):
        """Generate and upload the GPG key

        Args:
            lock_acquired (boolean): If True, don't acquire the lock before
                generating the key.
        Returns:
            Promise
        """
        if not lock_acquired:
            self._key_lock.acquire()

        try:

            key_name = 'bajoo-storage-%s' % self.id
            _logger.debug('generate new key for container #%s ...' % self.id)
            key = yield encryption.create_key(key_name, None, container=True)
            yield self._encrypt_and_upload_key(key)
        finally:
            if lock_acquired:
                self._key_lock.release()

    @reduce_coroutine()
    def _update_key(self, use_local_members=False):
        _logger.debug('Update key for container #%s ...' % self.id)
        key = yield self._get_encryption_key()

        yield self._encrypt_and_upload_key(key, use_local_members)

    @staticmethod
    def _from_json(session, json_object):
        from .my_bajoo import MyBajoo
        from .team_share import TeamShare

        id, name = json_object.get('id', ''), json_object.get('name', '')
        is_encrypted = json_object.get('is_encrypted', False)

        # prevent the string 'True' instead of boolean value True
        if type(is_encrypted) is not bool:
            is_encrypted = (is_encrypted == 'True')

        cls = MyBajoo if name == "MyBajoo" else TeamShare

        return cls(session, id, name, is_encrypted)

    @classmethod
    @reduce_coroutine()
    def create(cls, session, name, encrypted=True):
        """
        Create a new Container on Bajoo server.

        Args:
            session (bajoo.api.session.Session): user session
            name (str): the name of the new container to be created.
            encrypted(boolean, optional):
                if set the container will be encrypted.

        Returns:
            Promise<Container>: the newly created container.
        """

        response = yield session.send_api_request(
            'POST', '/storages',
            data={'name': name, 'is_encrypted': encrypted})

        container_result = response.get('content', {})
        container = Container._from_json(session, container_result)

        if container.is_encrypted:
            yield container._generate_key()

        yield container
        return

    @staticmethod
    @reduce_coroutine()
    def find(session, container_id):
        """
        Find a container by its id.

        Args:
            session (bajoo.api.session.Session):
                a user's session to whom the container belongs.
            container_id (str): id of the container to search.

        Returns:
            Promise<Container>: the container found, Promise<None> otherwise.
        """
        try:
            result = yield session.send_api_request(
                'GET', '/storages/%s' % container_id)
        except Exception as error:
            # TODO: throw ContainerNotFoundError
            _logger.debug('Error when search for container (%s, %s)',
                          error.code, error.message)
            yield None
            return

        result_container = result.get('content', {})
        yield Container._from_json(session, result_container)
        return

    @staticmethod
    def list(session):
        """
        Get the list of share folders of a user.

        Args:
            session (bajoo.api.session.Session):
                a user's session to whom share folders belong.

        Returns:
            Future<list<Container>>
        """

        def _on_get_storages(result):
            result_storages = result.get('content', {})
            storage_list = [Container._from_json(session, result_storage)
                            for result_storage in result_storages]

            return storage_list

        return session.send_api_request('GET', '/storages') \
            .then(_on_get_storages)

    @reduce_coroutine()
    def delete(self):
        """Delete this container from Bajoo server."""
        yield self._session.send_api_request('DELETE',
                                             '/storages/%s' % self.id)
        yield None

    def get_stats(self):
        raise NotImplemented()

    @reduce_coroutine()
    def list_files(self, prefix=None):
        """
        List all files in this container.

        Args:
            prefix (str): when defined, this will search only for files
                whose names start with this prefix.

        Returns:
            Promise<array>: the request result.
        """
        response = yield self._session.send_storage_request(
            'GET', '/storages/%s' % self.id,
            headers={'Accept': 'application/json'},
            params={'prefix': prefix})

        yield response.get('content', {})

    @reduce_coroutine()
    def download(self, path):
        """
        Download a file in this container.

        Args:
            path (str): the path to the file to be downloaded.

        Returns:
            Promise<dict, TemporaryFile>: metadata and the temporary file
            downloaded.
        """
        url = '/storages/%s/%s' % (self.id, path)

        if self.is_encrypted:
            encryption_key = yield self._get_encryption_key()

        result = yield self._session.download_storage_file('GET', url)
        md5_hash = result.get('headers', {}).get('etag')
        metadata = {'hash': md5_hash}
        downloaded_file = result.get('content')

        if self.is_encrypted:
            decrypted_file = yield encryption.decrypt(downloaded_file,
                                                      encryption_key)
            yield metadata, decrypted_file
        else:
            yield metadata, downloaded_file

    @reduce_coroutine()
    def upload(self, path, file):
        """Upload a file in this container.

        Note: if a file-like object is passed as `file`, it will be
        automatically closed after the upload.

        Args:
            path (str): the path to the file will be placed on the server.
            file (str / File-like): the path to the local file to be uploaded
            (if type is str), or file content to be uploaded.
        Returns:
            Promise<dict>: Metadata dict, containing the md5 hash of the
                uploaded file.
        """
        url = '/storages/%s/%s' % (self.id, path)

        if self.is_encrypted:
            encryption_key = yield self._get_encryption_key()
            file = yield encryption.encrypt(file, recipients=[encryption_key])

        result = yield self._session.upload_storage_file('PUT', url, file)
        # TODO: check the upload result (using md5 sum)

        md5_hash = result.get('headers', {}).get('etag')
        yield {'hash': md5_hash}

    @reduce_coroutine()
    def remove_file(self, path):
        """
        Delete a file object in this container.

        Args:
            path (str): the relative file path inside the container.

        Returns:
            Promise<None>
        """
        url = '/storages/%s/%s' % (self.id, path)
        yield self._session.send_storage_request('DELETE', url)
        yield None


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from .session import Session

    session1 = Session.create_session('stran+20@bajoo.fr',
                                      'stran+20@bajoo.fr').result()
    _logger.debug('Storage list: %s', Container.list(session1).result())
    _logger.debug('Storage files: %s', Container.list(session1).result()[0]
                  .list_files().result())

    container_id = '5cf75964e49a4f4c809aaf2d80cc8178'
    _logger.debug('Search container by id %s: %s', container_id,
                  Container.find(session1, container_id).result())
    _logger.debug('Search container by id %s: %s', 'invalid_id',
                  Container.find(session1, 'invalid_id').result())

    from random import choice
    from string import ascii_lowercase

    # generate a random container name
    def gen(length):
        return ''.join(choice(ascii_lowercase) for _ in range(length))

    new_container_name = gen(16)
    container_created = Container.create(session1, new_container_name).result()
    _logger.debug('Created container: %s', container_created)

    # upload a file to the new created container
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile() as tmp:
        file_content = 'Hello world! ' + gen(32)
        _logger.debug('Temporary file content: %s', file_content)
        tmp.write(file_content)
        tmp.seek(0)
        container_created.upload('tmp.txt', tmp).result()

    # get file list again to verify uploaded file
    _logger.debug('New container\'s files: %s',
                  container_created.list_files().result())

    # download the uploaded file
    _logger.debug('Download file: %s',
                  container_created.download('tmp.txt').result()[1].read())

    # delete the uploaded file
    _logger.debug('Delete file: %s',
                  container_created.remove_file('tmp.txt').result())

    # get statistics of the new created container
    # _logger.debug('Container\'s statistics: %s',
    # container_created.get_stats().result())

    # test delete created container
    _logger.debug('Deleted container: %s', container_created.delete().result())
