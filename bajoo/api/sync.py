# -*- coding: utf-8 -*-

import logging
import os.path
import sys

from .container import Container
from ..common.periodic_task import PeriodicTask
from ..filesync.filepath import is_hidden_part_in_path

_logger = logging.getLogger(__name__)


def container_list_updater(session, on_added_containers, on_removed_containers,
                           on_unchanged_containers=None,
                           last_known_list=None, check_period=600):
    """Detect changes in the user's container list.

    When one or more containers are added to the list, the
    `on_added_containers` callback is called. When a containers is removed
    from the list, the `on_removed_containers` is called.

    Args:
        session
        on_added_containers (Callable): called with the list of added
            containers in parameters, each time a new container is detected.
        on_removed_containers (callable): called with the list of container's
            id who've been removed in parameters, each time a container is
                removed.
        on_unchanged_containers (callable, optional): If set, it will be called
            on the first iteration, with the containers who hasn't been
            changed.
        last_known_list (List[str], optional): list of container's ids
            already known. If not set, all containers will be considered as
            'new'.
    Returns:
        PeriodicTask: a task who update the list (by calling the callbacks) at
            a regular interval. It must be started using `start()`, and
            stopped with `stop()`
    """

    def update_list(pt, last_known_list):
        first_call = not pt.context
        if not first_call:
            last_known_list = pt.context['id_list']

        f = Container.list(session)
        container_list = f.result()

        added_list = [c for c in container_list if c.id not in last_known_list]
        id_list = [c.id for c in container_list]
        removed_id_list = [id for id in last_known_list
                           if id not in id_list]

        if first_call and on_unchanged_containers:
            unchanged_list = [c for c in container_list
                              if c.id in last_known_list]
            if unchanged_list:
                on_unchanged_containers(unchanged_list)
        if added_list:
            on_added_containers(added_list)
        if removed_id_list:
            on_removed_containers(removed_id_list)
        pt.context['id_list'] = id_list

    return PeriodicTask('Container list updater', check_period, update_list,
                        last_known_list or [])


def files_list_updater(container, container_path, on_new_files,
                       on_changed_files, on_deleted_files,
                       on_initial_files=None, last_known_list=None,
                       check_period=600):
    """Detect changes in the files of a container.

    Each time a file is added, modified or removed, the corresponding callback
    is called.

    Args:
        session
        on_new_files (callable):
        on_changed_files (callable):
        on_deleted_files (callable):
        on_initial_files (callable, optional):
        last_known_list (dict(str, str), optional): known file. the key is the
            file's name and the value is the md5 sum.
    Returns:
        PeriodicTask: a task who update the list (by calling the callbacks) at
            a regular interval. It must be started using `start()`, and
            stopped with `stop()`
    """

    def update_list(pt, last_known_list):
        first_call = not pt.context
        if not first_call:
            last_known_list = pt.context['known_list']

        new_files = []
        changed_files = []
        initial_files = []
        deleted_files = []

        new_known_list = {}

        list_files = container.list_files().result()

        for f in list_files:
            abs_f = f['name']

            if sys.platform in ['win32', 'cygwin', 'win64']:
                abs_f = abs_f.replace('\\', '/')

            abs_f = os.path.join(container_path, abs_f)

            if is_hidden_part_in_path(container_path, abs_f):
                continue

            new_known_list[f['name']] = f['hash']
            if f['name'] in last_known_list:
                if f['hash'] != last_known_list[f['name']]:
                    changed_files.append(f)
                elif first_call and on_initial_files:
                    initial_files.append(f)
            else:
                new_files.append(f)

        for key in last_known_list:
            if key not in new_known_list:
                deleted_files.append({'name': key,
                                      'hash': last_known_list[key]})

        if new_files:
            on_new_files(new_files)
        if changed_files:
            on_changed_files(changed_files)
        if first_call and initial_files:
            on_initial_files(initial_files)
        if deleted_files:
            on_deleted_files(deleted_files)

        pt.context['known_list'] = new_known_list

    return PeriodicTask('File list updater %s' % container.id, check_period,
                        update_list, last_known_list or [])


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

    session = Session.from_user_credentials('test+20@bajoo.fr',
                                            'test+20@bajoo.fr').result()
    updater = container_list_updater(session, added, removed,
                                     check_period=5)

    print('Storage list of test+20@bajoo.fr will be checked all 5 '
          'seconds ...')
    updater.start()

    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        updater.stop()


if __name__ == '__main__':
    main()
