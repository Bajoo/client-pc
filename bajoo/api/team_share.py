# -*- coding: utf-8 -*-
import json
import logging

from .container import Container


_logger = logging.getLogger(__name__)

permission = {
    'NO_RIGHTS': {'read': False, 'write': False, 'admin': False},
    'READ_ONLY': {'read': True, 'write': False, 'admin': False},
    'READ_WRITE': {'read': True, 'write': True, 'admin': False},
    'ADMIN': {'read': True, 'write': True, 'admin': True}
}


class TeamShare(Container):
    """
    This class represent a private share folder between some specific users.
    The user who creates this share will be set as its admin by default,
    then he/she can add access to this share for other users.
    """

    def __init__(self, session, container_id, name):
        Container.__init__(self, session, container_id, name)

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        return "<TeamShare '%s' (id=%s)>" % (self.name, self.id)

    @classmethod
    def create(cls, session, name, encrypted=True):
        share = super(TeamShare, cls).create(session, name)

        # TODO: Handle encryption choice
        return share

    def list_members(self):
        """
        Get the list of users who have access to this container.

        Returns (Future<array>):
            The array of user permissions associated with this container,
            which follows this format:
            [{
                'user' (str): <user_email>
                'admin' (bool): True/False
                'write' (bool): True/False
                'read' (bool): True/False
            }]
        """

        url = '/storages/%s/rights' % self.id

        def _on_receive_response(result):
            # Delete 'scope' element in results
            for element in result.get('content', {}):
                del element['scope']

            return result

        return self._session.send_api_request('GET', url) \
            .then(_on_receive_response)

    def _set_permissions(self, user, permissions):
        """
        Set a user's permissions for this share.
        """
        url = '/storages/%s/rights/users/%s' % (self.id, user)

        # TODO: Handle the 404 error when user email is not found.
        return self._session.send_api_request(
            'PUT', url,
            headers={'Content-type': 'application/json'},
            data=json.dumps(permissions))

    def add_member(self, user, permissions):
        """
        Give access to this share to a user.

        Args:
            user (str): email of the user to modify permissions.
            permissions (dict): a dictionary which contains permissions
                following this format:
                {
                    'admin' (bool): True/False
                    'write' (bool): True/False
                    'read' (bool): True/False
                }

        Returns (Future<dict>): the permissions dictionary for this user.
        """
        return self._set_permissions(user, permissions)

    def change_permissions(self, user, permissions):
        """
        Change permissions of a user in this share.

        Args:
            user (str): email of the user to modify permissions.
            permissions (dict): a dictionary which contains permissions
                following this format:
                {
                    'admin' (bool): True/False
                    'write' (bool): True/False
                    'read' (bool): True/False
                }

        Returns (Future<dict>): the permissions dictionary for this user.
        """
        return self._set_permissions(user, permissions)

    def remove_member(self, user):
        """
        Remove access to this share of a user.

        Args:
            user (str): email of the user to remove access.

        Returns (Future<dict>): the permissions dictionary for this user.
        """
        return self._set_permissions(user, permission['NO_RIGHTS'])


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from .session import Session

    session1 = Session.create_session('stran+20@bajoo.fr',
                                      'stran+20@bajoo.fr').result()

    from random import choice
    from string import ascii_lowercase

    # generate a random container name
    def gen(length):
        return ''.join(choice(ascii_lowercase) for _ in range(length))

    new_container_name = gen(16)
    container_created = TeamShare.create(session1, new_container_name).result()
    _logger.debug('Created container: %s', container_created)

    # Add stran+21@bajoo.fr as admin
    _logger.debug('Add stran+21@bajoo.fr: %s',
                  container_created.add_member(
                      'stran+21@bajoo.fr', permission['ADMIN'])
                  .result().get('content', {}))

    # get list of rights in the newly created container
    # which should contain stran+21@bajoo.fr as admin
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result().get('content', {}))

    _logger.debug('Change rights of stran+21@bajoo.fr: %s',
                  container_created.change_permissions(
                      'stran+21@bajoo.fr', permission['READ_WRITE'])
                  .result().get('content', {}))

    # get list of rights in the newly created container
    # which should contain stran+21@bajoo.fr as writer
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result().get('content', {}))

    _logger.debug('Remove access of stran+21@bajoo.fr: %s',
                  container_created.remove_member('stran+21@bajoo.fr')
                  .result().get('content', {}))

    # get list of rights in the newly created container
    # which should NOT contain stran+21@bajoo.fr.
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result().get('content', {}))

    # delete created container
    _logger.debug('Deleted container: %s', container_created.delete().result())
