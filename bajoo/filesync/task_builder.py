# -*- coding: utf-8 -*-

from ..index.folder_node import FolderNode
from ..index.hints import DeletedHint, DestMoveHint, SourceMoveHint
from ..index.hint_builder import HintBuilder
from .added_local_files_task import AddedLocalFilesTask
from .added_remote_files_task import AddedRemoteFilesTask
from .folder_task import FolderTask
from .moved_local_files_task import MovedLocalFilesTask
from .removed_local_files_task import RemovedLocalFilesTask
from .removed_remote_files_task import RemovedRemoteFilesTask


class TaskBuilder(object):
    """Create sync task by acquiring node and release node when task is done.

    A task is created from the node, depending of the node's type and its
    state (new or existing node, type of hints).
    When the task has been executed, it can release the reserved node(s).

    A task can reserve several nodes, by example when there is a "Move" hint.
    """

    @classmethod
    def build_from_node(cls, local_container, node):
        """Create the best suited sync task for the target node.

        The type of task will depends of the type of node and the hints set by
        external events.
        After this call, the node is not yet acquired. `acquire_from_task()`
        should be called before executing the task.

        Note:
            - This method must be called with the IndexTree's lock acquired.

        Args:
            local_container (LocalContainer): container owning the node.
            node (BaseNode): node to sync.
        Returns:
            Task: sync task, executable by the filesync service.
        """
        container = local_container.container

        node_path = node.get_full_path()
        if isinstance(node, FolderNode):
            task = FolderTask(local_container, node)
        else:
            if node.local_hint:
                if isinstance(node.local_hint, DestMoveHint):
                    node = node.local_hint.source_node
                    node_path = node.get_full_path()

                if isinstance(node.local_hint, SourceMoveHint):
                    dest_path = node.local_hint.dest_node.get_full_path()
                    task = MovedLocalFilesTask(container,
                                               (node_path, dest_path,),
                                               local_container)
                elif isinstance(node.local_hint, DeletedHint):
                    task = RemovedLocalFilesTask(container, (node_path,),
                                                 local_container)
                else:  # ModifiedHint
                    task = AddedLocalFilesTask(container, (node_path,),
                                               local_container)
            elif node.remote_hint:
                if isinstance(node.remote_hint, DestMoveHint):
                    node = node.remote_hint.source_node
                    node_path = node.get_full_path()

                # if isinstance(node.remote_hint, SourceMoveHint):
                #     # TODO: no support for remove Move events.
                #     dest_path = node.remote_hint.dest_node.get_full_path()

                if isinstance(node.remote_hint, DeletedHint):
                    task = RemovedRemoteFilesTask(container, (node_path,),
                                                  local_container)
                else:  # ModifiedHint
                    task = AddedRemoteFilesTask(container, (node_path,),
                                                local_container)
            else:
                task = AddedLocalFilesTask(container, (node_path,),
                                           local_container)

        return task

    @classmethod
    def acquire_from_task(cls, node, task):
        """Acquire the node and all related nodes used by the task.

        For most of the tasks, only the primary node is acquired. If there are
        some "Move" hints, hint pairs can be split in (Deleted, Modified)
        couple.
        If the task is of type "MovedLocalFilesTask", both source and
        destination nodes are acquired by the task.

        Note:
            - This method must be called with the IndexTree's lock acquired.
            - After an acquisition, nodes's hints are reset to None. If they
            are needed by the task, they should be copied before that.

        Args:
            node (BaseNode): primary target of the task.
            task: sync task that will take care of the node(s).
        """

        if isinstance(task, MovedLocalFilesTask):
            HintBuilder.break_coupled_hints(node, HintBuilder.SCOPE_REMOTE)
            if isinstance(node.local_hint, SourceMoveHint):
                # acquire destination node
                dest_node = node.local_hint.dest_node
                dest_node.task = task
                dest_node.remote_hint = None
                dest_node.local_hint = None
            else:
                # acquire source node
                source_node = node.local_hint.source_node
                source_node.task = task
                source_node.remote_hint = None
                source_node.local_hint = None

        else:
            HintBuilder.break_coupled_hints(node)

        # acquire target node
        node.task = task
        node.remote_hint = None
        node.local_hint = None
