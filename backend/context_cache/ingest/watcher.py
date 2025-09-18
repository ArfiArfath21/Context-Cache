"""Filesystem watcher that emits ingestion tasks."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

FileEventCallback = Callable[[str, Path], None]


@dataclass
class WatchedSource:
    id: str
    path: Path
    include: list[str]
    exclude: list[str]
    callback: FileEventCallback


class SourceEventHandler(PatternMatchingEventHandler):
    """Dispatch filesystem events to the ingest pipeline."""

    def __init__(self, source: WatchedSource) -> None:
        super().__init__(
            patterns=source.include or ["*"],
            ignore_patterns=source.exclude,
            ignore_directories=False,
            case_sensitive=False,
        )
        self.source = source

    def on_created(self, event: FileSystemEvent) -> None:  # pragma: no cover - requires filesystem
        if not event.is_directory:
            self.source.callback(self.source.id, Path(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:  # pragma: no cover - requires filesystem
        if not event.is_directory:
            self.source.callback(self.source.id, Path(event.src_path))

    def on_moved(self, event: FileSystemEvent) -> None:  # pragma: no cover - requires filesystem
        if not event.is_directory:
            self.source.callback(self.source.id, Path(event.dest_path))

    def on_deleted(self, event: FileSystemEvent) -> None:  # pragma: no cover - requires filesystem
        if not event.is_directory:
            self.source.callback(self.source.id, Path(event.src_path))


class Watcher:
    """High-level wrapper around watchdog observers."""

    def __init__(self) -> None:
        self._observer: BaseObserver = Observer()
        self._lock = threading.Lock()
        self._sources: Dict[str, WatchedSource] = {}
        self._started = False

    def add_source(
        self,
        source_id: str,
        path: Path,
        callback: FileEventCallback,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        recursive: bool = True,
    ) -> None:
        normalized_path = path.expanduser().resolve()
        watched = WatchedSource(
            id=source_id,
            path=normalized_path,
            include=include or ["*"],
            exclude=exclude or [],
            callback=callback,
        )
        handler = SourceEventHandler(watched)
        with self._lock:
            self._observer.schedule(event_handler=handler, path=str(normalized_path), recursive=recursive)
            self._sources[source_id] = watched

    def remove_source(self, source_id: str) -> None:
        with self._lock:
            watched = self._sources.pop(source_id, None)
            if watched is None:
                return
            self._observer.unschedule_all()
            # Re-register remaining watchers
            for remaining in self._sources.values():
                handler = SourceEventHandler(remaining)
                self._observer.schedule(handler, str(remaining.path), recursive=True)

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._observer.start()
            self._started = True

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self._observer.stop()
            self._observer.join(timeout=5)
            self._started = False

    def close(self) -> None:
        self.stop()
        with self._lock:
            self._observer.unschedule_all()
            self._sources.clear()


__all__ = ["Watcher", "FileEventCallback"]
