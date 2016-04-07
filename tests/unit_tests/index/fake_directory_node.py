# -*- coding: utf-8 -*-


class FakeDirectoryNode(object):

    def __init__(self):
        self.unlocker = None
        self.triggered = False
        self.waiting_nodes = []
        self.removed_nodes = []
        self.prior_nodes = []
        self.waiting_for_node = None

    def unlock(self, owner):
        self.unlocker = owner

    def trigger_waiting_task(self):
        self.triggered = True

    def add_waiting_node(self, node, prior_node=False):
        self.waiting_nodes.append((node, prior_node))

    def remove_waiting_node(self, node):
        self.removed_nodes.append(node)

    def set_prior(self, node):
        self.prior_nodes.append(node)
