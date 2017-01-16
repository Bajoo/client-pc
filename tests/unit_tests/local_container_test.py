
from bajoo.container_model import ContainerModel
from bajoo.local_container import ContainerStatus, LocalContainer


class TestLocalContainer(object):

    def test_lc_has_default_status_stopped(self):
        lc = LocalContainer(ContainerModel('ID', 'Name'), None)
        assert lc.status == ContainerStatus.SYNC_STOP

    def test_lc_fire_signal_when_on_status_change(self):
        lc = LocalContainer(ContainerModel('ID', 'Name'), None)
        passed = []

        def _assert(status):
            assert status == ContainerStatus.SYNC_PROGRESS
            passed.append(True)

        lc.status_changed.connect(_assert)
        lc.status = ContainerStatus.SYNC_PROGRESS
        assert passed

    def test_lc_do_not_fire_signal_if_status_not_changed(self):
        lc = LocalContainer(ContainerModel('ID', 'Name'), None)
        lc.status = ContainerStatus.SYNC_STOP

        def _assert():
            assert False  # callback should not be executed.

        lc.status_changed.connect(_assert)
        lc.status = ContainerStatus.SYNC_STOP

        assert lc.status == ContainerStatus.SYNC_STOP
