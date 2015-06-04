# -*- coding: utf-8 -*-


def connect_or_register(ui_factory):
    """Start the process of connection and/or registration.

    This process will follow all necessary steps to register (optionally) and
    connect the user, according to his will.
    If the process can be done with the already present informations, the
    operation will be transparent for the user.
    If not (ie: no credentials saved), the UI handler factory, received in
    parameter, will be called to create an UI handler. this UI handler will be
    used to communicate with the user.

    The default behavior is to connect using the saved credentials. If it
    doesn't work, the user is asked to give his credentials, or create a new
    account (registration). In case of registration, the user will be
    automatically connected after the account creation.

    The Future will resolve only when the user will be completely connected,
    with a valid session and a valid GPG key, present in local device.
    If the user never connects, by not responding to UI handler messages, then
    the returned future will never resolve.

    Args:
        ui_factory (callable<UIHandlerOfConnection>): callable who returns an
            UIHandlerOfConnection. This function will never be called more
            than one.
    Returns:
        Future<session>: A connected, valid session.
    """
    raise NotImplementedError()
