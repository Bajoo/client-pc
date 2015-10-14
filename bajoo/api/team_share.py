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

    Attributes:
        members (list): list of sharing members with the following format:
            [{
                'user' (str): <user_email>
                'admin' (bool): True/False
                'write' (bool): True/False
                'read' (bool): True/False
            }]
            Note that the list is not loaded at Container creation. It's must
            be loaded with a call to list_members() before any use.
    """

    def __init__(self, session, container_id, name, encrypted=True):
        Container.__init__(self, session, container_id, name, encrypted)
        self.members = []

    def __repr__(self):
        """
        Override the representational string of the container object.
        """
        s = "<TeamShare '%s' (id=%s, encrypted=%s)>" % \
            (self.name, self.id, self.is_encrypted)
        if not isinstance(s, str):
            # Python 2 with type unicode.
            s = s.encode('utf-8')
        return s

    @classmethod
    def create(cls, session, name, encrypted=True):
        """
        Returns: Future<TeamShare>
        """
        share_future = super(TeamShare, cls) \
            .create(session, name, encrypted)

        return share_future

    def list_members(self):
        """
        Get the list of users who have access to this container.

        This method will set or update the `self.members` attributes.

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
            members = result.get('content', [])

            for element in members:
                del element['scope']

            self.members = members
            return members

        return self._session.send_api_request('GET', url) \
            .then(_on_receive_response)

    def _set_permissions(self, user, permissions, then_update_key=True):
        """
        Set a user's permissions for this share.

        Args:
            user (str): user email
            permission (object): permission object, e.g.
                {
                    'admin' (bool): True/False,
                    'write' (bool): True/False,
                    'read' (bool): True/False
                }
            then_update_key (boolean):
                True (default) if you want to update & re-upload the key.
        """
        url = '/storages/%s/rights/users/%s' % (self.id, user)

        def _on_receive_response(result):
            return result.get('content', {})

        # TODO: Handle the 404 error when user email is not found.
        f = self._session.send_api_request(
            'PUT', url,
            headers={'Content-type': 'application/json'},
            data=json.dumps(permissions)) \
            .then(_on_receive_response)
        if self.is_encrypted and then_update_key:
            return f.then(lambda _: self._update_key())
        else:
            return f

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

    def remove_member(self, user, is_self_quit=False):
        """
        Remove access to this share of a user.

        Args:
            user (str): email of the user to remove access.
            is_self_quit (boolean):
                True if it's user who chose to quit instead of being
                kicked out by another admin.

        Returns (Future<dict>): the permissions dictionary for this user.
        """

        def _set_permission(_):
            return self._set_permissions(
                user, permission['NO_RIGHTS'], then_update_key=False)

        if is_self_quit:
            # remove user in the list first
            for entry in self.members:
                if entry['user'] == user:
                    self.members.remove(entry)
                    break

            # then update the encryption key
            # & send request to server
            return self._update_key(use_local_members=True) \
                .then(_set_permission)
        else:
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
    container_created = TeamShare \
        .create(session1, new_container_name, False) \
        .result()
    _logger.debug('Created container: %s', container_created)

    # Add stran+21@bajoo.fr as admin
    _logger.debug('Add stran+21@bajoo.fr: %s',
                  container_created.add_member(
                      'stran+21@bajoo.fr', permission['ADMIN'])
                  .result())

    # get list of rights in the newly created container
    # which should contain stran+21@bajoo.fr as admin
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result())

    _logger.debug('Change rights of stran+21@bajoo.fr: %s',
                  container_created.change_permissions(
                      'stran+21@bajoo.fr', permission['READ_WRITE'])
                  .result())

    # get list of rights in the newly created container
    # which should contain stran+21@bajoo.fr as writer
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result())

    _logger.debug('Remove access of stran+21@bajoo.fr: %s',
                  container_created.remove_member('stran+21@bajoo.fr')
                  .result())

    # get list of rights in the newly created container
    # which should NOT contain stran+21@bajoo.fr.
    _logger.debug('New containter\'s rights: %s',
                  container_created.list_members()
                  .result())

    # delete created container
    _logger.debug('Deleted container: %s', container_created.delete().result())
