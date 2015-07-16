# -*- coding: utf-8 -*-

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class FileWatcher(FileSystemEventHandler):
    """Watch all modification of a folder in the filesystem.

    Note: a file creation raises 3 events: file created, file changed, and
        directory changed. Also, directory events are often "duplicates" of
        file events. As the Bajoo API doesn't support (yet) empty directories,
        directory events are ignored.
    """

    def __init__(self, local_container, on_new_files, on_changed_files,
                 on_moved_files, on_deleted_files):
        """
        Args:
            local_container (LocalContainer): it's used to get the path to
                listen, and the directories to exclude.
        """
        self._local_container = local_container
        self._observer = Observer()
        self._observer.schedule(self, path=local_container.path,
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
        if event.is_directory:
            return
        self._on_moved_files(event.src_path, event.dest_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self._on_new_files(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._on_deleted_files(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._on_changed_files(event.src_path)


def main():
    from functools import partial
    import time
    from .local_container import LocalContainer

    def callback(event, src, dest=None):
        if not dest:
            print('An event happened: %s %s' % (event, src))
        else:
            print('An event happened: %s %s -> %s' % (event, src, dest))

    watcher = FileWatcher(LocalContainer(1, 'CWD', '.'),
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
