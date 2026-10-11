"""File watching via watchdog (the chokidar part of the original)."""
import os
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import logger

_IGNORED_DIRS = {"node_modules", ".jibun", ".git", "dist", "coverage"}
_IGNORED_SUFFIXES = (".log", ".tmp", ".temp")


def is_ignored(path, root) -> bool:
    """Dotfiles/dot-folders, dependency/build folders, logs and temp files are not the learner's work."""
    try:
        rel = Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        rel = Path(path)
    parts = rel.parts
    if any(p.startswith(".") or p in _IGNORED_DIRS for p in parts):
        return True
    return bool(parts) and parts[-1].endswith(_IGNORED_SUFFIXES)


class _Handler(FileSystemEventHandler):
    def __init__(self, root, on_change):
        self.root, self.on_change = root, on_change

    def _emit(self, kind, path):
        if not is_ignored(path, self.root):
            self.on_change(kind, os.fsdecode(path))

    def on_created(self, e):
        self._emit("addDir" if e.is_directory else "add", e.src_path)

    def on_modified(self, e):
        if not e.is_directory:
            self._emit("change", e.src_path)

    def on_deleted(self, e):
        self._emit("unlinkDir" if e.is_directory else "unlink", e.src_path)

    def on_moved(self, e):
        self._emit("unlinkDir" if e.is_directory else "unlink", e.src_path)
        self._emit("addDir" if e.is_directory else "add", e.dest_path)


def start_watcher(project_path, on_change: Callable[[str, str], None]) -> Observer:
    """Starts watching; returns the observer (call .stop() then .join() to close it)."""
    logger.info("Watching project for changes...")
    logger.info("Press Ctrl+C to stop.\n")
    observer = Observer()
    observer.schedule(_Handler(project_path, on_change), str(project_path), recursive=True)
    observer.start()
    return observer
