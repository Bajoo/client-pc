# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


class Container(object):
    def __init__(self, session, container_id, name):
        self._session = session
        self.id = container_id
        self.name = name

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        return "<Container '%s' (id=%s)>" % (self.name, self.id)

    @staticmethod
    def create(session, name):
        def _on_create_returned(response):
            container_result = response.get('content', {})
            return Container(session, container_result.get('id', ''),
                             container_result.get('name', ''))

        return session.send_api_request(
            'POST', '/storages', data={'name': name}) \
            .then(_on_create_returned)

    @staticmethod
    def find(session, container_id):
        """
        Find a container by its id.

        Args:
            session: a user's session to whom the container belongs.
            container_id: id of the container to search.

        Returns Future<Container>: the container found, Future<None> otherwise.
        """

        def _on_get_containers(result):
            result_container = result.get('content', {})
            return Container(session, result_container.get('id', ''),
                             result_container.get('name', ''))

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
            session: a user's session to whom share folders belong.

        Returns:
            Future<list<Container>>
        """

        def _on_get_storages(result):
            result_storages = result.get('content', {})
            storage_list = [Container(session, result_storage.get('id', ''),
                                      result_storage.get('name', ''))
                            for result_storage in result_storages]

            return storage_list

        return session.send_api_request('GET', '/storages') \
            .then(_on_get_storages)

    def delete(self):
        return self._session \
            .send_api_request('DELETE', '/storages/%s' % self.id) \
            .then(lambda _: None)

    def get_stats(self):
        raise NotImplemented()

    def list_files(self, prefix=None):
        return self._session.send_api_request(
            'GET', '/storages/%s' % self.id,
            headers={'Accept': 'application/json'})

    def download(self, path):
        url = '/storages/%s/%s' % (self.id, path)
        return self._session.download_storage_file('GET', url)

    def upload(self, path, file):
        url = '/storages/%s/%s' % (self.id, path)
        return self._session.upload_storage_file('PUT', url, file)


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
                  container_created.download('tmp.txt').result().get(
                      'content').read())

    # get statistics of the new created container
    # _logger.debug('Container\'s statistics: %s',
    #              container_created.get_stats().result())

    # test delete created container
    _logger.debug('Deleted container: %s', container_created.delete().result())
