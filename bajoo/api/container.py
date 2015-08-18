# -*- coding: utf-8 -*-

import logging

from ..common.future import Future, wait_all
from .. import encryption
from ..network.errors import HTTPNotFoundError
from . import User


_logger = logging.getLogger(__name__)


class Container(object):
    """
    Represent a Bajoo container, which can be the MyBajoo folder,
    a TeamShare or a PublicShare.
    This should always be used as an abstract class.
    """

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

        self._encryption_key = None

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        return "<Container '%s' (id=%s, encrypted=%s)>" % \
               (self.name, self.id, str(self.is_encrypted))

    def _get_encryption_key(self):
        """get the encryption key and returns it.

        If the key is not present in local, it will be downloaded.

        Returns:
            Future<AsyncKey>: container key
        """
        if not self._encryption_key:

            def dl_key_error(error):
                if isinstance(error, HTTPNotFoundError):
                    _logger.debug('Container key not found (404)')
                    f = self._generate_key()
                    return f.then(lambda _: self._encryption_key)
                raise error

            def on_key_downloaded(result):
                key_content = result.get('content')
                _logger.debug('Key of container #%s downloaded' % self.id)
                return encryption.decrypt(key_content)

            def on_key_decrypted(key_content):
                key = encryption.AsymmetricKey.load(key_content)
                self._encryption_key = key
                return key

            _logger.debug('Download key of container #%s ...' % self.id)
            key_url = '/storages/%s/.key' % self.id
            f = self._session.download_storage_file('GET', key_url)
            f = f.then(on_key_downloaded)
            return f.then(on_key_decrypted, dl_key_error)

        return Future.resolve(self._encryption_key)

    def _generate_key(self):
        """Generate and upload the GPG key

        Returns:
            Future
        """
        key_name = 'bajoo-storage-%s' % self.id

        def extract_key_members(members):
            return wait_all(
                [User(member['user'], self._session).get_public_key()
                 for member in members])

        def get_owner_key():
            f = User.load(self._session)
            f = f.then(lambda user: user.get_user_info().then(lambda _: user))
            return f.then(lambda user: user.get_public_key())

        def encrypt_key(key):
            self._encryption_key = key
            key_content = key.export(secret=True)

            # TODO: code smell: we shouldn't use methods of child classes.
            if hasattr(self, 'list_members'):
                f = self.list_members().then(extract_key_members)
            else:
                f = get_owner_key()
                f = f.then(lambda key: [key])

            def encrypt(recipients):
                return encryption.encrypt(key_content, recipients)

            return f.then(encrypt)

        def upload_key(key_content):
            key_url = '/storages/%s/.key' % self.id
            _logger.debug('Key for container #%s generated.' % self.id)
            return self._session.send_storage_request(
                'PUT', key_url, data=key_content)

        _logger.debug('generate new key for container #%s ...' % self.id)
        f = encryption.create_key(key_name, None, container=True)
        f = f.then(encrypt_key)
        return f.then(upload_key)

    @staticmethod
    def _from_json(session, json_object):
        from .my_bajoo import MyBajoo
        from .team_share import TeamShare

        id, name = json_object.get('id', ''), json_object.get('name', '')
        is_encrypted = json_object.get('is_encrypted', True)
        cls = MyBajoo if name == "MyBajoo" else TeamShare

        return cls(session, id, name, is_encrypted)

    @classmethod
    def create(cls, session, name, encrypted=True):
        """
        Create a new Container on Bajoo server.

        Args:
            session (bajoo.api.session.Session): user session
            name (str): the name of the new container to be created.
            encrypted(boolean, optional):
                if set the container will be encrypted.

        Returns Future<Container>: the newly created container.
        """

        def _on_create_returned(response):
            container_result = response.get('content', {})
            container = cls(session, container_result.get('id', ''),
                            container_result.get('name', ''),
                            encrypted=container_result.get(
                                'is_encrypted', True))
            if container.is_encrypted:
                return container._generate_key().then(lambda _: container)
            return container

        return session.send_api_request(
            'POST', '/storages',
            data={'name': name, 'is_encrypted': encrypted}) \
            .then(_on_create_returned)

    @staticmethod
    def find(session, container_id):
        """
        Find a container by its id.

        Args:
            session (bajoo.api.session.Session):
                a user's session to whom the container belongs.
            container_id (str): id of the container to search.

        Returns Future<Container>: the container found, Future<None> otherwise.
        """

        def _on_get_containers(result):
            result_container = result.get('content', {})
            return Container._from_json(session, result_container)

        def _on_error(error):
            # TODO: throw ContainerNotFoundError
            _logger.debug('Error when search for container (%s, %s)',
                          error.code, error.message)
            return None

        return session.send_api_request('GET', '/storages/%s' % container_id) \
            .then(_on_get_containers, _on_error)

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

    def delete(self):
        """Delete this container from Bajoo server."""
        return self._session \
            .send_api_request('DELETE', '/storages/%s' % self.id) \
            .then(lambda _: None)

    def get_stats(self):
        raise NotImplemented()

    def list_files(self, prefix=None):
        """
        List all files in this container.

        Args:
            prefix (str): when defined, this will search only for files
                whose names start with this prefix.

        Returns Future<array>: the request result.
        """

        def _on_list_file_result(response):
            return response.get('content', {})

        return self._session.send_storage_request(
            'GET', '/storages/%s' % self.id,
            headers={'Accept': 'application/json'},
            params={'prefix': prefix}).then(_on_list_file_result)

    def download(self, path):
        """
        Download a file in this container.

        Args:
            path (str): the path to the file to be downloaded.

        Returns <Future<dict, TemporaryFile>>: metadata and the temporary file
            downloaded.
        """
        url = '/storages/%s/%s' % (self.id, path)

        def download_file(_key=None):
            return self._session.download_storage_file('GET', url)

        def format_result(result):
            md5_hash = result.get('headers', {}).get('etag')
            return {'hash': md5_hash}, result.get('content')

        def decrypt_file(data):
            metadata, encrypted_file = data
            return (metadata,
                    encryption.decrypt(encrypted_file, self._encryption_key))

        if self.is_encrypted:
            f = self._get_encryption_key()
            f = f.then(download_file)
            f = f.then(format_result)
            f = f.then(decrypt_file)
        else:
            f = download_file()
            f = f.then(format_result)
        return f

    def upload(self, path, file):
        """Upload a file in this container.

        Note: if a file-like object is passed as `file`, it will be
        automatically closed after the upload.

        Args:
            path (str): the path to the file will be placed on the server.
            file (str / File-like): the path to the local file to be uploaded
            (if type is str), or file content to be uploaded.
        Returns:
            Future<dict>: Metadata dict, containing the md5 hash of the
                uploaded file.
        """
        url = '/storages/%s/%s' % (self.id, path)

        def encrypt_file(encryption_key):
            return encryption.encrypt(file, recipients=[encryption_key])

        def upload_file(encrypted_file):
            return self._session.upload_storage_file('PUT', url,
                                                     encrypted_file)

        def format_result(result):
            md5_hash = result.get('headers', {}).get('etag')
            return {'hash': md5_hash}

        # TODO: check the upload result (using md5 sum)

        if self.is_encrypted:
            f = self._get_encryption_key()
            f = f.then(encrypt_file)
        else:
            f = Future.resolve(file)

        f = f.then(upload_file)
        return f.then(format_result)

    def remove_file(self, path):
        """
        Delete a file object in this container.

        Args:
            path (str): the relative file path inside the container.

        Returns (Future<None>)
        """
        url = '/storages/%s/%s' % (self.id, path)
        return self._session \
            .send_storage_request('DELETE', url) \
            .then(lambda _: None)


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
