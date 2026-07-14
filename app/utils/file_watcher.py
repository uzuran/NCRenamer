"""Polling-based file watcher — zero extra dependencies.

Runs a single daemon thread that checks file modification times every
``poll_interval_ms`` milliseconds.  When a mtime change is detected the
registered callback is marshalled back to the tkinter main thread via
``root.after(0, callback)`` so all UI updates remain thread-safe.

Usage::

    watcher = FileWatcher(root, poll_interval_ms=500)
    watcher.watch(path_to_file, my_callback)
    watcher.start()          # call once; thread is a daemon so it dies with the app
    ...
    watcher.stop()           # call in WM_DELETE_WINDOW handler
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable


class FileWatcher:
    """Poll file mtimes in a daemon thread; schedule callbacks on the tk main thread."""

    def __init__(self, root, poll_interval_ms: int = 500) -> None:
        self._root = root
        self._poll_ms = poll_interval_ms
        # path → (last_known_mtime, callback)
        self._watched: dict[Path, tuple[float, Callable[[], None]]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def watch(self, path: Path, callback: Callable[[], None]) -> None:
        """Register *path* to be watched with *callback* on change.

        Safe to call before or after :meth:`start`.  Replaces any previous
        registration for the same path.
        """
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        with self._lock:
            self._watched[path] = (mtime, callback)

    def unwatch(self, path: Path) -> None:
        """Remove *path* from the watch list.  No-op if not watched."""
        with self._lock:
            self._watched.pop(path, None)

    def start(self) -> None:
        """Start the background polling thread.  Idempotent."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the polling thread to exit.  Non-blocking; safe to call multiple times."""
        self._running = False

    def acknowledge_write(self, path: Path) -> None:
        """Update the known mtime for *path* without firing a callback.

        Call this immediately after your code writes to *path* to prevent the
        next poll from treating the write as an external change.
        """
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        with self._lock:
            if path in self._watched:
                _, cb = self._watched[path]
                self._watched[path] = (mtime, cb)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(self._poll_ms / 1000.0)
            self._check_all()

    def _check_all(self) -> None:
        with self._lock:
            snapshot = list(self._watched.items())
        for path, (last_mtime, callback) in snapshot:
            try:
                current_mtime = path.stat().st_mtime
            except OSError:
                continue
            if current_mtime != last_mtime:
                with self._lock:
                    if path in self._watched:
                        self._watched[path] = (current_mtime, callback)
                try:
                    self._root.after(0, callback)
                except Exception:
                    # Tkinter root may have been destroyed before this fires.
                    pass
