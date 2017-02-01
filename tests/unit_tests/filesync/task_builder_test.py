# -*- coding: utf-8 -*-

from bajoo.filesync.moved_local_files_task import MovedLocalFilesTask
from bajoo.filesync.task_builder import TaskBuilder
from bajoo.index.hints import (DeletedHint, DestMoveHint, ModifiedHint,
                               SourceMoveHint)


class FakeNode(object):
    def __init__(self, local_hint=None, remote_hint=None):
        self.local_hint = local_hint
        self.remote_hint = remote_hint
        self.state = None
        self.task = None


class FakeTask(object):
    pass


class FakeMovedTask(MovedLocalFilesTask):
    """Fake task which do nothing, subclass of MovedLocalFilesTask"""
    def __init__(self):
        # MovedLocalFilesTask.__init__ is voluntary not called.
        pass

    def __repr__(self):
        return 'FakeMovedTask()'


class TestTaskBuilder(object):

    def test_acquire_node_from_added_task(self):
        node = FakeNode()
        task = FakeTask()
        TaskBuilder.acquire_from_task(node, task)
        assert node.task is task

    def test_acquire_node_from_added_task_reset_hints(self):
        node = FakeNode(local_hint=ModifiedHint(), remote_hint=DeletedHint())
        task = FakeTask()
        TaskBuilder.acquire_from_task(node, task)
        assert node.task is task

    def test_acquire_node_from_task_will_break_links_between_nodes(self):
        node = FakeNode()
        dest_node = FakeNode(local_hint=DestMoveHint(source_node=node))
        node.local_hint = SourceMoveHint(dest_node=dest_node)
        task = FakeTask()

        TaskBuilder.acquire_from_task(node, task)
        assert node.task is task
        assert dest_node.task is None
        assert isinstance(dest_node.local_hint, ModifiedHint)
        assert node.local_hint is None
        assert node.remote_hint is None

    def test_acquire_node_from_src_move_task_will_acquire_two_nodes(self):
        node = FakeNode()
        dest_node = FakeNode(local_hint=DestMoveHint(source_node=node))
        node.local_hint = SourceMoveHint(dest_node=dest_node)

        task = FakeMovedTask()

        TaskBuilder.acquire_from_task(node, task)
        assert node.task is task
        assert dest_node.task is task
        assert node.local_hint is None
        assert dest_node.local_hint is None

    def test_acquire_node_from_dest_move_task_will_acquire_two_nodes(self):
        node = FakeNode()
        source_node = FakeNode(local_hint=SourceMoveHint(dest_node=node))
        node.local_hint = DestMoveHint(source_node=source_node)

        task = FakeMovedTask()

        TaskBuilder.acquire_from_task(node, task)
        assert node.task is task
        assert source_node.task is task
        assert source_node.remote_hint is None
        assert source_node.local_hint is None
        assert node.local_hint is None
        assert node.remote_hint is None
