#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import logging
import os
import sys

from .abstract_task import _Task
from ..common import config
from .filepath import is_path_allowed, is_hidden
from ..promise import Promise
from .task_consumer import add_task

TASK_NAME = 'sync'

_logger = logging.getLogger(__name__)


class SyncTask(_Task):

    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.nodes[0]
        src_path = os.path.join(self.local_path, target.get_complete_path())
        subtasks = []

        # clean mark on file node
        for file_node in target.traverse_only_file_node():
            file_node.visited = False

        # iterate on file in directory
        for dirpath, dirnames, filenames in os.walk(src_path):
            # no file in this directory
            if len(filenames) == 0:
                continue

            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, self.local_path)

                if config.get('exclude_hidden_files') and is_hidden(abs_path):
                    continue

                if sys.platform in ['win32', 'cygwin', 'win64']:
                    rel_path = rel_path.replace('\\', '/')

                if not is_path_allowed(rel_path):
                    continue

                node = self.local_container.index.get_node(rel_path)
                create_mode = True

                if node is not None:
                    create_mode = False
                    node.visited = True

                task = self._create_push_task(rel_path, create_mode)
                subtasks.append(add_task(task))

        # search for deleted files
        for file_node in target.traverse_only_file_node():
            if file_node.visited:
                file_node.visited = False
                continue

            task = self._create_a_remove_task(file_node.rel_path)
            subtasks.append(add_task(task, priority=True))

        self._release_index()

        if subtasks:
            results = yield Promise.all(subtasks)
            failed_tasks = itertools.chain(*results)
            self._task_errors.extend(failed_tasks)
