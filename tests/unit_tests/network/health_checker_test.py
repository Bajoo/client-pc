# -*- coding: utf-8 -*-

import pytest
import threading

from bajoo.network.health_checker import HealthChecker
from bajoo.promise import CancelledError, Promise, TimeoutError
from bajoo.network.errors import NetworkError


class MockExecutor(object):
    """A set of mocked execute_request functions."""

    @staticmethod
    def bad(_request):
        """Request always in error."""
        return Promise.reject(NetworkError())

    @staticmethod
    def good(_request):
        """Request always OK."""
        return Promise.resolve({'code': 200, 'content': ':)', 'headers': {}})

    @staticmethod
    def only_selected_host(host):
        """Make an executor who accept only request made to a specific host.

        Returns
            callable: execute_request function.
        """
        def execute_request(request):
            if request.host == host:
                return Promise.resolve(None)
            else:
                return Promise.reject(NetworkError())
        return execute_request

    @staticmethod
    def pass_after_activation():
        """Make an executor who accept request after a flag has be set.

        Returns
            tuple(dict, callable): context with a "pass" flags,
                and the execute_request callback
        """
        context = {'pass': False}

        def execute_request(request):
            if context['pass']:
                return Promise.resolve(None)
            else:
                return Promise.reject(NetworkError())
        return context, execute_request


class TestHealthChecker(object):

    def test_health_check_on_valid_server(self):
        checker = HealthChecker(MockExecutor.good)

        promise = checker.check('https://server.bajoo.fr')
        promise.result(0.01)
        checker.stop()

    def test_health_check_on_broken_server(self):
        checker = HealthChecker(MockExecutor.bad)
        promise = checker.check('https://not-exists.bajoo.fr')
        with pytest.raises(TimeoutError):
            promise.result(0.01)
        checker.stop()

    def test_health_check_on_several_hosts(self):
        exec_request = MockExecutor.only_selected_host('www.bajoo.fr')
        checker = HealthChecker(exec_request)
        p1 = checker.check('https://no.bajoo.fr')
        p2 = checker.check('https://www.bajoo.fr')
        p3 = checker.check('https://no.bajoo.fr')

        with pytest.raises(TimeoutError):
            assert p1.result(0.01)
        p2.result(0.01)
        with pytest.raises(TimeoutError):
            assert p3.result(0.01)
        checker.stop()

    def test_health_checker_use_high_priority_request(self):
        def execute_request(req):
            assert req.priority < 10
            return Promise.resolve(None)

        checker = HealthChecker(execute_request)
        checker.check('https://server.bajoo.fr')
        checker.stop()

    def test_health_checker_reuse_promise(self):
        context, execute_request = MockExecutor.pass_after_activation()
        checker = HealthChecker(execute_request)
        p1 = checker.check('https://srv1.bajoo.fr')
        p2 = checker.check('https://srv1.bajoo.fr')
        p3 = checker.check('https://srv2.bajoo.fr')
        assert p1 is p2
        assert p1 is not p3
        checker.stop()

    @pytest.mark.skipif(not pytest.config.getvalue('slowtest'), reason='rr')
    def test_health_checker_wait_network_recovering(self):
        context = {'count': 0}

        def execute_request(request):
            context['count'] += 1
            if context['count'] < 3:
                return Promise.reject(NetworkError())
            else:
                return Promise.resolve(None)

        checker = HealthChecker(execute_request)
        p1 = checker.check('https://srv1.bajoo.fr')
        p1.result(5)
        assert context['count'] == 3
        checker.stop()

    def test_health_checker_stop_timers(self):
        initial_nb_threads = len(threading.enumerate())

        checker = HealthChecker(MockExecutor.bad)
        promise = checker.check('https://not-exists.bajoo.fr')

        with pytest.raises(TimeoutError):
            promise.result(0.01)
        assert len(threading.enumerate()) > initial_nb_threads

        checker.stop()
        with pytest.raises(CancelledError):
            promise.result(0.01)
        assert len(threading.enumerate()) == initial_nb_threads
