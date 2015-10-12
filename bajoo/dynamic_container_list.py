# -*- coding: utf-8 -*-

import logging
from threading import Lock as Lock
import os

from .common.i18n import _
from .common.path import get_data_dir
from .api.sync import container_list_updater
from .local_container import LocalContainer
from .container_model import ContainerModel


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

    The self._local_list is a list of LocalContainers. theirs 'container'
    attributes are set as soon as possible. If the attribute doesn't exists,
    the element should be considered being loaded.
    """

    def __init__(self, session, user_profile, notify, start_container,
                 stop_container):
        """
        Args:
            session (Session)
            user_profile (UserProfile): user's profile. Used to remember
                containers (and theirs settings) between executions.
            notify (callable): Notify the user about an event. take three
                parameters: the summary, the text body, and a boolean to
                specify if it's an error.
            start_container (callable): callback called when the LocalContainer
                is ready. Receive a fully loaded LocalContainer in
                parameters.
            stop_container (callable): callback called when a container is
                removed. Receive LocalContainer in parameters.
        """
        self.user_profile = user_profile
        self._notify = notify
        self._list_path = os.path.join(get_data_dir(), 'container_list.json')
        self._local_list = []
        self._list_lock = Lock()
        self._start_container = start_container
        self._stop_container = stop_container

        # NOTE: since user_profile is not tread-safe, all calls to user_profile
        # methods must be done using the Lock `self._list_lock`.
        local_list_data = self.user_profile.get_all_containers()
        self._local_list = [
            LocalContainer(c.id, c.name, c.path,
                           do_not_sync=c.do_not_sync)
            for c in local_list_data.values()]

        local_id_list = list(local_list_data)

        self._updater = container_list_updater(session,
                                               self._on_added_containers,
                                               self._on_removed_containers,
                                               self._init_containers,
                                               local_id_list)
        self._updater.start()

    def _init_containers(self, container_list):
        """Called by the updater at start with a list of unchanged containers.

        Args:
            list of Container: the list fo all containers who were already
                present during the last Bajoo execution.
        """
        _logger.debug('Container(s) loaded: %s', container_list)

        with self._list_lock:
            for local_container in self._local_list:
                local_id = local_container.id
                c = next((c for c in container_list if c.id == local_id), None)
                local_container.container = c
                if c:
                    if local_container.path is None:
                        new_path = local_container.create_folder(
                            self.user_profile.root_folder_path, c.name)
                        if new_path is None:
                            self._notify(
                                _('Error when adding new share'),
                                _('Unable to create a folder for %s:\n%s'
                                  % (c.name, local_container.error_msg)),
                                is_error=True)
                        else:
                            # As we've a LocalContainer, model cant be None.
                            model = self.user_profile.get_container(local_id)
                            model.path = new_path
                            self.user_profile.set_container(model)

                            self._pre_start_container(local_container)
                    elif not local_container.check_path():
                        self._notify(
                            _('Error on share sync'),
                            _("Unable to sync the share %s:\n%s")
                            % (c.name, local_container.error_msg),
                            is_error=True)
                    else:
                        self._pre_start_container(local_container)

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
                local_container.container = c
                c_path = local_container.create_folder(
                    self.user_profile.root_folder_path, c.name)

                model = ContainerModel(c.id, name=c.name,
                                       path=local_container.path)
                self.user_profile.set_container(model.id, model)

                if c_path is None:
                    self._notify(_('Error when adding new share'),
                                 _('Unable to create a folder for %s:\n%s'
                                   % (c.name, local_container.error_msg)),
                                 is_error=True)
                else:
                    self._pre_start_container(local_container)
                self._local_list.append(local_container)

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
                self.user_profile.remove_container(container_id)

                to_remove = [c for c in self._local_list
                             if c.id == container_id]
                for local_container in to_remove:
                    self._stop_container(local_container)
                    self._local_list.remove(local_container)

    def _pre_start_container(self, local_container):
        # TODO: remove do_not_sync from LocalContainer.
        # Should be easy; don't create LC if it shouldn't be sync !
        if local_container.do_not_sync:
            local_container.status = LocalContainer.STATUS_STOPPED
        else:
            self._start_container(local_container)

    def stop(self):
        self._updater.stop()

    def refresh(self, callback=None):
        """Force refresh immediately.

        Args:
            callback (Callable, optional): if set, it will be called without
                argument as soon as the refresh is done.
        """
        self._updater.apply_now(callback)

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
    from .user_profile import UserProfile

    logging.basicConfig()

    def notify(summary, body, is_error=False):
        print('NOTIF %s: %s' % ('ERROR' if is_error else 'INFO', summary))
        print(body)

    def start_container(container):
        print('Start container %s' % container)

    def stop_container(local):
        print('Stop container %s (%s)' % (local.id, local.name))

    session = Session.create_session('stran+20@bajoo.fr',
                                     'stran+20@bajoo.fr').result()

    user_profile = UserProfile('stran+20@bajoo.fr')
    if not user_profile.root_folder_path:
        # DynamicContainerList need it to load new containers
        user_profile.root_folder_path = './tmp'
    dyn_list = DynamicContainerList(session, user_profile, notify,
                                    start_container, stop_container)
    try:
        while True:
            time.sleep(0.3)
    except KeyboardInterrupt:
        dyn_list.stop()


if __name__ == "__main__":
    main()
