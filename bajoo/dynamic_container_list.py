# -*- coding: utf-8 -*-

import json
import logging
from threading import Lock as Lock
import os
import errno

from .common.i18n import _
from .common.path import get_data_dir
from .api.sync import container_list_updater

_logger = logging.getLogger(__name__)


class DynamicContainerList(object):
    """Keep sync the local and remote lists of containers.

    The class contains the up-to-date list of containers, and can be used to
    list and see the container's status.

    It will detect differences between the last sync of containers list, check
    path for already known containers et creates new folders for new
    containers.
    It will also prevent the user about added or removed containers, as well
    as error path.

    All local, know containers are registered in the file
    `container_list.json`

    The file has the following format:
    [{
      'id': '123456',
      'name': 'My Container'
      'path': '/home/user/Bajoo/my_container/'
    },
    { ... }]

    The elements in self._local_list contains one more attribute: 'container'.
    'container' is set as soon as possible. If it doesn't exists, the element
    should be considered being loaded.
    """

    def __init__(self, session, notify):
        """
        Args:
            session (Session)
            notify (callable): Notify the user about an event. take two
                parameters: the summary and the text body.
        """
        self._notify = notify
        self._list_path = os.path.join(get_data_dir(), 'container_list.json')
        self._local_list = []
        self._list_lock = Lock()

        try:
            with open(self._list_path) as list_file:
                self._local_list = json.load(list_file)
        except IOError as e:
            if e.errno is errno.ENOENT:
                _logger.debug('Container list file not found.')
            else:
                _logger.warning('Unable to open the container list file:',
                                exc_info=True)
        except ValueError:
            _logger.warning('The container list file is not valid:',
                            exc_info=True)

        local_id_list = [c['id'] for c in self._local_list]

        self._updater = container_list_updater(session,
                                               self._on_added_containers,
                                               self._on_removed_containers,
                                               self._init_containers,
                                               local_id_list)
        self._updater.start()

    def _save_local_list(self):
        """Save the local list file."""
        try:
            with open(self._list_path, 'w') as list_file, self._list_lock:
                local_list = [{'id': c['id'],
                               'name': c['name'],
                               'path': c['path']} for c in self._local_list]
                json.dump(local_list, list_file)
        except IOError:
            _logger.warning("The container list file can't be saved:",
                            exc_info=True)

    def _init_containers(self, containers_list):
        _logger.debug('Container(s) loaded: %s', containers_list)

        with self._list_lock:
            for item in self._local_list:
                for c in containers_list:
                    if c.id == item['id']:
                        item['container'] = c
                        break

        # TODO: find and check the path of each container
        # If the path is not valid, or if there isn't an index file in the
        # folder, we must inform the user and set the status to ERROR.
        # TODO: start each container

    def _on_added_containers(self, added_containers):
        _logger.info('New container(s) detected: %s', added_containers)

        if len(added_containers) == 1:
            self._notify(_('New Bajoo share added'),
                         _('You have a new Bajoo share:\n%s') %
                         added_containers[0].name)
        else:
            body = _('You have %s new Bajoo shares:') % len(added_containers)
            body += '\n\t- %s' % added_containers[0].name
            body += '\n\t- %s' % added_containers[1].name
            if len(added_containers) == 3:
                body += '\n\t- %s' % added_containers[2].name
            elif len(added_containers) > 3:
                body += '\n\t'
                body += _('and %s others') % (len(added_containers) - 2)
            self._notify(_('New Bajoo shares added'), body)

        with self._list_lock:
            for c in added_containers:
                self._local_list.append({
                    'id': c.id,
                    'name': c.name,
                    'path': None,
                    'container': c
                })
        self._save_local_list()

        # TODO: associate folders to the containers
        # Generate path for the container's name.
        # If a path is taken, generate a new one, unless the index file match.
        # TODO: start the containers.

    def _on_removed_containers(self, removed_containers):
        _logger.info('container(s) removed: %s', removed_containers)

        if len(removed_containers) == 1:
            title = _('A Bajoo share have been removed.')
            body = _('Either the share has been deleted or your permissions '
                     'have been revoked.')
        else:
            title = _('%s Bajoo shares have been removed.'
                      % len(removed_containers))
            body = _('Either the shares have been deleted, or your permissions'
                     ' have been revoked.')
        self._notify(title, body)

        with self._list_lock:
            for container_id in removed_containers:
                to_remove = [c for c in self._local_list
                             if c['id'] == container_id]
                for c in to_remove:
                    self._local_list.remove(c)

        # TODO: properly stop the containers (if started).

        self._save_local_list()

    def stop(self):
        self._updater.stop()

    def get_list(self):
        """returns the list of containers.

        Returns:
            list of dict: each dict represent a container. It contains:
             - id (str)
             - name (str)
             - path (str): corresponding path on the disk.
             - container (bajoo.api.Container): if set, container instance.
             - status (str)

         Note: the returned container instance is not a copy but a reference.
         It will not be modified directly by the dynamic list.
        """
        with self._list_lock:
            # Note: item.container are copied by reference.
            return [dict(c) for c in self._local_list]


def main():
    import time
    from .api.session import Session

    logging.basicConfig()

    def notify(summary, body):
        print('NOTIFICATION: %s' % summary)
        print(body)

    session = Session.create_session('stran+20@bajoo.fr',
                                     'stran+20@bajoo.fr').result()
    dyn_list = DynamicContainerList(session, notify)
    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        dyn_list.stop()


if __name__ == "__main__":
    main()
