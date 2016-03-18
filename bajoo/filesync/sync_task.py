#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import logging
import os

from .abstract_task import _Task
from .added_local_files_task import PushTaskMixin
from ..common import config
from .filepath import is_path_allowed, is_hidden
from ..promise import Promise
from .removed_local_files_task import RemovedTaskMixin
from .task_consumer import add_task

TASK_NAME = 'sync'

_logger = logging.getLogger(__name__)


class SyncTask(_Task, PushTaskMixin, RemovedTaskMixin):
    @staticmethod
    def get_type():
        return TASK_NAME

    def _apply_task(self):
        _logger.debug('Execute task %s' % self)

        target = self.target_list[0]
        src_path = os.path.join(self.local_path, target.rel_path)
        subtasks = []

        for name in os.listdir(src_path):
            abs_path = os.path.join(src_path, name)
            rel_path = os.path.relpath(abs_path, self.local_path)
            task = None

            if config.get('exclude_hidden_files') and is_hidden(abs_path):
                continue
            if os.path.isdir(abs_path):
                self.index_fragment = {
                    k: v for (k, v) in self.index_fragment.items()
                    if not k.startswith('%s/' % rel_path)}
                task = SyncTask(self.container, (rel_path,),
                                self.local_container, self.display_error_cb,
                                parent_path=target.rel_path)
            else:
                if not is_path_allowed(rel_path):
                    continue

                create_mode = True
                if rel_path in self.index_fragment:
                    # TODO: don't log when file is not modified !
                    del self.index_fragment[rel_path]

                    # if file exists in the directory traversal,
                    # we want to trigger an error if it's removed
                    # during the task
                    create_mode = False

                task = self._create_push_task(rel_path, create_mode)

            if task:
                subtasks.append(add_task(task, priority=True))

        # locally removed items, present in the index, but not in local.
        for child_path in self.index_fragment:
            task = self._create_a_remove_task(child_path)
            subtasks.append(add_task(task, priority=True))

        self._release_index()

        if subtasks:
            results = yield Promise.all(subtasks)
            failed_tasks = itertools.chain(*filter(None, results))
            failed_tasks = list(failed_tasks)
            if failed_tasks:
                self._task_errors = failed_tasks
        yield None
        return
