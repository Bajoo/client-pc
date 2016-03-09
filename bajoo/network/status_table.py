# -*- coding: utf-8 -*-


class StatusTable(object):
    """Table containing networks status and shares error states.

    Attributes:
        global_status (boolean): if True, the network is operational.
            Otherwise, there is a global network problem.
        hosts (dict): a list of status per host. The key is the HTTP host
            (eg: storage.bajoo.fr). If an host is
            not in the dict, it's the first request addressed to this host.
    """

    def __init__(self):

        self.global_status = True
        self.hosts = {}

    def allow_request(self, request):
        """Check if a request should be allowed or not.

        The purpose of rejecting requests is to prevents flooding the network
        when there is a problem, as well as rejecting network promises faster
        than if the request have been sent.

        Args:
            request (Request): request which will be send.
        Returns:
            boolean: True if the request can be sent, False if not.
        """
        if not self.global_status:
            return False

        # TODO: check by host
        return True

    def update(self, request, error=None):
        """Update status according to the result of the request.

        Args:
            request (Request): request terminated (either by successfully
                returning a result, or by raising a exception).
            error (Exception, optional): exception raised by the request, if
                any.
        """
        if not error:
            self.global_status = True
        # TODO: implement
        pass
