# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, session, storage_id, name):
        self._session = session
        self.id = storage_id
        self.name = name

    def __repr__(self):
        """
        Override the representational string of the storage object.
        """
        return "<Storage '%s' (id=%s)>" % (self.name, self.id)

    @staticmethod
    def create(session, name):
        raise NotImplemented()

    @staticmethod
    def find(session, container_id):
        raise NotImplemented()

    @staticmethod
    def list(session):
        """
        Get the list of share folders of a user.

        Args:
            session: a user's session to whom share folders belong.

        Returns:
            Future<list<Storage>>
        """

        def _on_get_storages(result):
            result_storages = result.get('content', {})
            storage_list = [Storage(session, result_storage.get('id', ''),
                                    result_storage.get('name', ''))
                            for result_storage in result_storages]

            return storage_list

        return session.send_api_request('GET', '/storages') \
            .then(_on_get_storages)

    def delete(self):
        raise NotImplemented()

    def get_stats(self):
        raise NotImplemented()

    def list_files(self, prefix=None):
        return self._session.send_api_request(
            'GET', '/storages/%s' % self.id,
            headers={'Accept': 'application/json'})

    def download(self, path):
        raise NotImplemented()

    def upload(self, path, file):
        raise NotImplemented()


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from .session import Session

    session1 = Session.create_session('stran+20@bajoo.fr',
                                      'stran+20@bajoo.fr').result()
    _logger.debug('Storage list: %s', Storage.list(session1).result())
    _logger.debug('Storage files: %s', Storage.list(session1).result()[0]
                  .list_files().result())
