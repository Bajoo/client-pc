# -*- coding: utf-8 -*-

import sys

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .filesync.filepath import is_path_allowed, is_hidden_part_in_path
from .common.strings import ensure_unicode


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

    def _ensure_unicode(self, msg):
        return ensure_unicode(msg, sys.getfilesystemencoding() or 'utf-8')

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()

    def on_moved(self, event):
        src_path = self._ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return

        dest_path = self._ensure_unicode(event.dest_path)
        if is_hidden_part_in_path(self._container.path, dest_path):
            return
        self._on_moved_files(src_path, dest_path)

    def on_created(self, event):
        src_path = self._ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if is_hidden_part_in_path(self._container.path, src_path):
            return
        self._on_new_files(src_path)

    def on_deleted(self, event):
        src_path = self._ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if is_hidden_part_in_path(self._container.path, src_path):
            return
        self._on_deleted_files(src_path)

    def on_modified(self, event):
        src_path = self._ensure_unicode(event.src_path)
        if event.is_directory or not is_path_allowed(src_path):
            return
        if is_hidden_part_in_path(self._container.path, src_path):
            return
        self._on_changed_files(src_path)


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
