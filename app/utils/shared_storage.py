"""Shared path helpers and OS-level file locking for JSON storage backends.

These utilities are used by MaterialRepository and TodoRepository (and any
future repository that stores data in the EXE directory).
"""

from __future__ import annotations

import contextlib
import sys
import threading
from pathlib import Path

# Per-path threading locks used by the Windows branch.
# On POSIX, fcntl.flock already provides inter-process safety on top of
# thread safety; on Windows we skip msvcrt (broken in PyInstaller) and
# use a threading.Lock instead.
_lock_registry: dict[str, threading.Lock] = {}
_registry_mutex = threading.Lock()


def exe_dir() -> Path:
    """Return the directory of the running executable / entry script.

    - ``python app.py``  →  parent of *app.py*
    - PyInstaller EXE (incl. via shortcut)  →  parent of the real *.exe*
      because ``sys.argv[0]`` always reflects the physical executable path,
      not the shortcut that launched it.
    """
    return Path(sys.argv[0]).resolve().parent


def _get_thread_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _registry_mutex:
        if key not in _lock_registry:
            _lock_registry[key] = threading.Lock()
        return _lock_registry[key]


if sys.platform == "win32":

    @contextlib.contextmanager
    def file_lock(lock_path: Path):
        """Exclusive lock via threading.Lock (Windows-safe, PyInstaller-compatible).

        msvcrt.locking raises EDEADLK inside PyInstaller frozen builds, so we
        use a module-level threading.Lock keyed by resolved path instead.
        This provides intra-process thread safety; for this single-user desktop
        app that is sufficient.
        """
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with _get_thread_lock(lock_path):
            yield

else:
    import fcntl as _fcntl

    @contextlib.contextmanager
    def file_lock(lock_path: Path):
        """Exclusive blocking lock using fcntl (POSIX)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a") as _f:
            _fcntl.flock(_f, _fcntl.LOCK_EX)
            try:
                yield
            finally:
                _fcntl.flock(_f, _fcntl.LOCK_UN)
