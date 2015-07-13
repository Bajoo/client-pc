# -*- coding: utf-8 -*-

import logging
from threading import Timer

from .container import Container

_logger = logging.getLogger(__name__)


class PeriodicTask(object):

    def __init__(self, delay, task, *args):
        self._delay = delay
        self._task = task
        self._args = args
        self._timer = None
        self._canceled = False

    def _exec_task(self, *args, **kwargs):
        try:
            self._args = self._task(*args, **kwargs)
        except:
            _logger.exception('Periodic task %s has raised exception' %
                              self._task)
        self._timer = Timer(self._delay, self._exec_task,
                            args=self._args)
        if not self._canceled:
            self._timer.start()

    def start(self):
        _logger.debug('Start periodic task %s', self._task)
        self._timer = Timer(0, self._exec_task, args=self._args)
        self._timer.start()

    def stop(self):
        _logger.debug('Stop periodic task %s', self._task)
        self._canceled = True
        self._timer.cancel()


def container_list_updater(session, on_added_containers, on_removed_containers,
                           on_unchanged_containers=None,
                           last_known_list=None, check_period=600):
    """Detect changes in the user's container list.

    When one or more containers are added to the list, the
    `on_added_containers` callback is called. When a containers is removed
    from the list, the `on_removed_containers` is called.

    Args:
        session
        on_added_containers (callable): called with the list of added
            containers in parameters, each time a new container is detected.
        on_removed_containers (callable): called with the list of container's
            id who've been removed in parameters, each time a container is
                removed.
        on_unchanged_containers (callable, optional): If set, it will be called
            on the first iteration, with the containers who hasn't been
            changed.
        last_known_list (list of str, optional): list of container's ids
            already known. If not set, all containers will be considered as
            'new'.
    Returns;
        PeriodicTask: a task who update the list (by calling the callbacks) at
            a regular interval. It must be started using `start()`, and
            stopped with `stop()`
    """

    def update_list(last_known_list, on_unchanged_containers=None):
        f = Container.list(session)
        container_list = f.result()

        added_list = [c for c in container_list if c.id not in last_known_list]
        id_list = [c.id for c in container_list]
        removed_id_list = [id for id in last_known_list
                           if id not in id_list]

        if on_unchanged_containers:
            unchanged_list = [c for c in container_list
                              if c.id in last_known_list]
            if unchanged_list:
                on_unchanged_containers(unchanged_list)
        if added_list:
            on_added_containers(added_list)
        if removed_id_list:
            on_removed_containers(removed_id_list)
        return [id_list]

    return PeriodicTask(check_period, update_list, last_known_list or [],
                        on_unchanged_containers)


def files_list_updater(container, on_new_files, on_changed_files,
                       on_deleted_files, on_initial_files=None,
                       last_known_list=None, check_period=600):
    """Detect changes in the files of a container.

    Each time a file is added, modified or removed, the corresponding callback
    is called.

    Args:
        session
        on_new_files (callable):
        on_changed_files (callable):
        on_deleted_files (callable):
        on_initial_files (callable, optional):
        last_known_list (list of str, optional):
    Returns;
        PeriodicTask: a task who update the list (by calling the callbacks) at
            a regular interval. It must be started using `start()`, and
            stopped with `stop()`
    """

    def update_list(last_known_list, on_initial_files=None):
        print('--- ---- ---')
        print(last_known_list, on_initial_files)

        list_files = container.list_files().result()
        print(list_files)

        # TODO: We need to reorganize the list

    return PeriodicTask(check_period, update_list, last_known_list or [],
                        on_initial_files)


def main():
    import time
    from .session import Session

    logging.basicConfig()

    def added(new_containers):
        print('New container(s):')
        for c in new_containers:
            print('\t%s' % c)

    def removed(deleted_containers):
        print('Removed container(s):\n\t%s' % deleted_containers)

    session = Session.create_session('stran+20@bajoo.fr',
                                     'stran+20@bajoo.fr').result()
    updater = container_list_updater(session, added, removed,
                                     check_period=5)

    print('Storage list of stran+20@bajoo.fr will be checked all 5 '
          'seconds ...')
    updater.start()

    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        updater.stop()

if __name__ == '__main__':
    main()
