# -*- coding: utf-8 -*-

from bajoo.common.signal import Signal


class HandlerMock(object):
    def __init__(self):
        self.call_counter = 0
        # args and kwargs are last call arguments.
        self.args = None
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.call_counter += 1
        self.args = args
        self.kwargs = kwargs


class TestSignal(object):

    def test_basic_handler(self):
        s = Signal()
        h = HandlerMock()
        s.connect(h)
        s.fire()
        assert h.call_counter is 1

    def test_signal_with_many_handler(self):
        s = Signal()
        handlers = [HandlerMock() for _ in range(10)]

        for h in handlers:
            s.connect(h)
        s.fire()
        for h in handlers:
            assert h.call_counter is 1

    def test_signal_fired_several_times(self):
        s = Signal()
        h = HandlerMock()
        s.connect(h)
        s.fire()
        s.fire()
        s.fire()
        assert h.call_counter is 3

    def test_signal_fired_with_args(self):
        s = Signal()
        h = HandlerMock()
        s.connect(h)
        s.fire('ARG1', 2, 3)
        assert h.call_counter is 1
        assert h.args == ('ARG1', 2, 3)

    def test_signal_fired_with_kwargs(self):
        s = Signal()
        h = HandlerMock()
        s.connect(h)
        s.fire(foo='bar', marco='polo')
        assert h.call_counter is 1
        assert h.kwargs == {'foo': 'bar', 'marco': 'polo'}

    def test_disconnect_handler(self):
        s = Signal()
        h1 = HandlerMock()
        h2 = HandlerMock()
        h3 = HandlerMock()

        s.connect(h1)
        s.connect(h2)
        s.fire(1)
        s.connect(h3)
        s.fire(2)
        s.disconnect(h1)
        s.fire(3)

        assert h1.call_counter is 2
        assert h2.call_counter is 3
        assert h3.call_counter is 2
        assert h1.args == (2,)
        assert h2.args == (3,)
        assert h3.args == (3,)

    def test_disconnect_not_connected_handler(self):
        s = Signal()
        h = HandlerMock()
        s.connect(h)
        assert s.disconnect(lambda: None) is False
        assert s.disconnect(h) is True

    def test_disconnect_all(self):
        s = Signal()
        h = HandlerMock()
        h2 = HandlerMock()
        s.connect(h)
        s.fire()
        s.connect(h2)
        s.disconnect_all()
        s.fire()
        assert h.call_counter == 1
        assert h2.call_counter == 0
