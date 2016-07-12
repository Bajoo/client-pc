# -*- coding: utf-8 -*-


from bajoo.network.proxy import prepare_proxy, PROXY_MODE_SYSTEM, \
    PROXY_MODE_MANUAL, PROXY_MODE_NO


class TestProxy(object):
    def test_no_proxy(self):
        ret = prepare_proxy(PROXY_MODE_NO)
        assert ret is not None
        assert type(ret) is dict
        assert len(ret) == 0

    def test_system_proxy(self):
        assert prepare_proxy(PROXY_MODE_SYSTEM) is None

    def test_http_proxy_without_password(self):
        settings = {
            'type': "HTTP",
            'url': "localhost",
            'port': "3128",
            'user': "",
            'password': ""
        }
        ret = prepare_proxy(PROXY_MODE_MANUAL, settings)
        assert ret is not None
        assert type(ret) is dict
        assert len(ret) == 1
        assert 'https' in ret
        assert ret['https'] == "http://localhost:3128"

    def test_http_proxy_with_password(self):
        settings = {
            'type': "HTTP",
            'url': "localhost",
            'port': "3128",
            'user': "user",
            'password': "pass"
        }
        ret = prepare_proxy(PROXY_MODE_MANUAL, settings)
        assert ret is not None
        assert type(ret) is dict
        assert len(ret) == 1
        assert 'https' in ret
        assert ret['https'] == "http://user:pass@localhost:3128"
