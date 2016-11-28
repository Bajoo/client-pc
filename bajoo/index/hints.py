# -*- coding: utf-8 -*-


class BaseHint(object):
    """Base class for IndexNode's hints about action relative to sync."""


class DeletedHint(BaseHint):
    """Node has been deleted."""


class ModifiedHint(BaseHint):
    """The node content has been added or modified.

    Note that the state can be incomplete and/or have irrelevant data.

    Attributes:
        new_state (Optional[Any]): if set, state data that should be used to
            determine the new state of the node. It will be used by the Task.
            The type of data depends of the node.
    """
    def __init__(self, new_state=None):
        BaseHint.__init__(self)
        self.new_data = new_state


class SourceMoveHint(BaseHint):
    """The node's content has been moved elsewhere.

    This node represent the source of the move action.

    Attributes:
        dest_node (BaseNode): reference to the destination node.
    """
    def __init__(self, dest_node=None):
        BaseHint.__init__(self)
        self.dest_node = dest_node


class DestMoveHint(BaseHint):
    """The node's content has been moved from elsewhere.

    This node represent the destination of the move action.

    Attributes:
        source_node (BaseNode): reference to the source node.
    """
    def __init__(self, source_node=None):
        BaseHint.__init__(self)
        self.source_node = source_node
