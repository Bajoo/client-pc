# -*- coding: utf-8 -*-


from bajoo.network.proxy import prepare_proxy, PROXY_MODE_SYSTEM, \
    PROXY_MODE_MANUAL, PROXY_MODE_NO


class TestProxy(object):
    def test_no_proxy(self, monkeypatch):
        config = {}
        config['proxy_mode'] = PROXY_MODE_NO
        monkeypatch.setattr("bajoo.network.proxy.config", config)
        ret = prepare_proxy()
        assert ret is not None
        assert type(ret) is dict
        assert len(ret) == 0

    def test_system_proxy(self, monkeypatch):
        config = {}
        monkeypatch.setattr("bajoo.network.proxy.config", config)
        config['proxy_mode'] = PROXY_MODE_SYSTEM
        assert prepare_proxy() is None

    def test_http_proxy_without_password(self, monkeypatch):
        config = {}
        monkeypatch.setattr("bajoo.network.proxy.config", config)
        config['proxy_mode'] = PROXY_MODE_MANUAL
        config['proxy_type'] = "HTTP"
        config['proxy_url'] = "localhost"
        config['proxy_port'] = "3128"
        config['proxy_user'] = ""
        config['proxy_password'] = ""
        ret = prepare_proxy()
        assert prepare_proxy() is not None
        assert type(ret) is dict
        assert len(ret) == 1
        assert 'https' in ret
        assert ret['https'] == "http://localhost:3128"

    def test_http_proxy_with_password(self, monkeypatch):
        config = {}
        monkeypatch.setattr("bajoo.network.proxy.config", config)
        config['proxy_mode'] = PROXY_MODE_MANUAL
        config['proxy_type'] = "HTTP"
        config['proxy_url'] = "localhost"
        config['proxy_port'] = "3128"
        config['proxy_user'] = "user"
        config['proxy_password'] = "pass"
        ret = prepare_proxy()
        assert prepare_proxy() is not None
        assert type(ret) is dict
        assert len(ret) == 1
        assert 'https' in ret
        assert ret['https'] == "http://user:pass@localhost:3128"
