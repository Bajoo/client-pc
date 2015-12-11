# -*- coding: utf-8 -*-

import os.path
import sys

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .filesync.filepath import is_path_allowed, is_hidden
from .common import config


def ensure_unicode(string):
    if type(string) == unicode:
        return string

    file_system_encoding = sys.getfilesystemencoding()

    if file_system_encoding is not None:
        return string.decode(file_system_encoding)

    try:
        return string.decode('UTF-8')
    except (LookupError, UnicodeDecodeError,):
        return string.decode()


class FileWatcher(FileSystemEventHandler):
    """Watch all modification of a folder in the filesystem.

    Note: a file creation raises 3 events: file created, file changed, and
        directory changed. Also, directory events are often "duplicates" of
        file events. As the Bajoo API doesn't support (yet) empty directories,
        directory events are ignored.
    """

    def __init__(self, container_model, on_new_files, on_changed_files,
                 on_moved_files, on_deleted_files):
        """
        Args:
            local_container (ContainerModel): it's used to get the path to
                listen, and the directories to exclude.
        """
        self._container = container_model
        self._observer = Observer()
        self._observer.schedule(self, path=container_model.path,
                                recursive=True)

        self._on_new_files = on_new_files
        self._on_changed_files = on_changed_files
        self._on_moved_files = on_moved_files
        self._on_deleted_files = on_deleted_files

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()

    def on_moved(self, event):
        src_path = ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return

        dest_path = ensure_unicode(event.dest_path)
        if self._is_ignored_target(dest_path):
            return
        self._on_moved_files(src_path, dest_path)

    def on_created(self, event):
        src_path = ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if self._is_ignored_target(src_path):
            return
        self._on_new_files(src_path)

    def on_deleted(self, event):
        src_path = ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if self._is_ignored_target(src_path):
            return
        self._on_deleted_files(src_path)

    def on_modified(self, event):
        src_path = ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if self._is_ignored_target(src_path):
            return
        self._on_changed_files(src_path)

    def _is_ignored_target(self, file_path):
        if not config.get('exclude_hidden_files'):
            return False

        container_path = os.path.normpath(self._container.path)

        p = file_path
        while p != container_path:
            if is_hidden(p):
                return True
            p = os.path.normpath(os.path.join(p, '..'))
        return False


def main():
    from functools import partial
    import time
    from .container_model import ContainerModel

    def callback(event, src, dest=None):
        if not dest:
            print('An event happened: %s %s' % (event, src))
        else:
            print('An event happened: %s %s -> %s' % (event, src, dest))

    watcher = FileWatcher(ContainerModel(1, name='CWD', path='.'),
                          partial(callback, 'CREATED'),
                          partial(callback, 'MODIFIED'),
                          partial(callback, 'MOVED'),
                          partial(callback, 'DELETED'))
    watcher.start()

    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        watcher.stop()

if __name__ == '__main__':
    main()
