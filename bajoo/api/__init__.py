# -*- coding: utf-8 -*-

from .user import User
from .session import Session
from .my_bajoo import MyBajoo
from .container import Container
from .team_share import TeamShare


if __name__ == '__main__':
    import logging
    from random import choice
    from string import ascii_lowercase

    logging.basicConfig(level=logging.DEBUG)

    # generate a random string
    random_id = ''.join(choice(ascii_lowercase) for _ in range(8))

    # Create a new account
    new_email = u'test+%s@bajoo.fr' % random_id
    new_password = u'password_test'

    print('> Create new user <%s>: %s' % (
        new_email, User.create(new_email, new_password).result()))

    # TODO: create a test case for deleting account

__all__ = [User, Session, Container, MyBajoo, TeamShare]
