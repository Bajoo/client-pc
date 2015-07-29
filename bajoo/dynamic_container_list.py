# -*- coding: utf-8 -*-

import io
import json
import logging
from threading import Lock as Lock
import os
import errno

from .common.i18n import _
from .common.path import get_data_dir
from .api.sync import container_list_updater
from .local_container import LocalContainer

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

    def __init__(self, session, notify, start_container,
                 stop_container):
        """
        Args:
            session (Session)
            notify (callable): Notify the user about an event. take two
                parameters: the summary and the text body.
            start_container (callable): callback called when the LocalContainer
                is ready. Receive (LocalContainer, api.Container) in
                parameters.
            stop_container (callable): callback called when a container is
                removed. Receive LocalContainer in parameters.
        """
        self._notify = notify
        self._list_path = os.path.join(get_data_dir(), 'container_list.json')
        self._local_list = []
        self._list_lock = Lock()
        self._start_container = start_container
        self._stop_container = stop_container

        local_list_data = []
        try:
            with io.open(self._list_path, encoding='utf-8') as list_file:
                local_list_data = json.load(list_file)
        except IOError as e:
            if e.errno is errno.ENOENT:
                _logger.debug('Container list file not found.')
            else:
                _logger.warning('Unable to open the container list file:',
                                exc_info=True)
        except ValueError:
            _logger.warning('The container list file is not valid:',
                            exc_info=True)

        self._local_list = [LocalContainer(c['id'], c['name'], c['path'])
                            for c in local_list_data]
        local_id_list = [c['id'] for c in local_list_data]

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
                local_list = [{'id': c.id,
                               'name': c.name,
                               'path': c.path} for c in self._local_list]
                json.dump(local_list, list_file)
        except IOError:
            _logger.warning("The container list file can't be saved:",
                            exc_info=True)

    def _init_containers(self, containers_list):
        _logger.debug('Container(s) loaded: %s', containers_list)

        with self._list_lock:
            for local_container in self._local_list:
                for c in containers_list:
                    if c.id == local_container.id:
                        if local_container.path is None:
                            new_path = local_container.create_folder(c.name)
                            if new_path is None:
                                self._notify(
                                    _('Error when adding new share'),
                                    _('Unable to create a folder for %s:\n%s'
                                      % (c.name, local_container.error_msg)))
                            else:
                                self._start_container(local_container, c)
                        elif not local_container.check_path():
                            self._notify(
                                _('Error on share sync'),
                                _('Unable to sync the share %s:\n%s'
                                  % (c.name, local_container.error_msg)))
                        else:
                            self._start_container(local_container, c)
                        break

        self._save_local_list()

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
                local_container = LocalContainer(c.id, c.name)
                c_path = local_container.create_folder(c.name)
                if c_path is None:
                    self._notify(_('Error when adding new share'),
                                 _('Unable to create a folder for %s:\n%s'
                                   % (c.name, local_container.error_msg)))
                else:
                    self._start_container(local_container, c)
                self._local_list.append(local_container)
        self._save_local_list()

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
                             if c.id == container_id]
                for local_container in to_remove:
                    self._stop_container(local_container)
                    self._local_list.remove(local_container)

        self._save_local_list()

    def stop(self):
        self._updater.stop()

    def get_list(self):
        """returns the list of containers.

        Returns:
            list of LocalContainer

         Note: the returned LocalContainer instances are not copy but
         references. They will not be modified directly by the dynamic list.
        """
        with self._list_lock:
            return list(self._local_list)


def main():
    import time
    from .api.session import Session

    logging.basicConfig()

    def notify(summary, body):
        print('NOTIFICATION: %s' % summary)
        print(body)

    def start_container(local, container):
        print('Start container %s' % container)

    def stop_container(local):
        print('Stop container %s (%s)' % (local.id, local.name))

    session = Session.create_session('stran+20@bajoo.fr',
                                     'stran+20@bajoo.fr').result()
    dyn_list = DynamicContainerList(session, notify,
                                    start_container, stop_container)
    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        dyn_list.stop()


if __name__ == "__main__":
    main()
