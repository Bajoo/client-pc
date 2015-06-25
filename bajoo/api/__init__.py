# -*- coding: utf-8 -*-
import logging

from .user import User


_logger = logging.getLogger(__name__)


def register(email, password):
    """
    Register a new Bajoo user using email & password.

    Returns:
        Future<None>
    """
    return User.create(email, password)


if __name__ == '__main__':
    logging.basicConfig()
    _logger.setLevel(logging.DEBUG)

    from random import choice
    from string import ascii_lowercase

    # generate a random string
    def gen(length):
        return ''.join(choice(ascii_lowercase) for _ in range(length))

    # Create a new account
    new_email = ''.join(['stran+', gen(8), '@bajoo.fr'])
    new_password = 'password_test'

    _logger.debug('Create new user <%s>: %s', new_email,
                  register(new_email, new_password).result())

    # TODO: create a test case for deleting account
