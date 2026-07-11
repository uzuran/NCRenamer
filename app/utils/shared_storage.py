"""Shared path helpers and OS-level file locking for JSON storage backends.

These utilities are used by MaterialRepository and TodoRepository (and any
future repository that stores data in the EXE directory).
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path


def exe_dir() -> Path:
    """Return the directory of the running executable / entry script.

    - ``python app.py``  →  parent of *app.py*
    - PyInstaller EXE (incl. via shortcut)  →  parent of the real *.exe*
      because ``sys.argv[0]`` always reflects the physical executable path,
      not the shortcut that launched it.
    """
    return Path(sys.argv[0]).resolve().parent


if sys.platform == "win32":
    import msvcrt as _msvcrt

    @contextlib.contextmanager
    def file_lock(lock_path: Path):
        """Exclusive blocking lock using msvcrt (Windows only)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not lock_path.exists():
            lock_path.write_bytes(b"\x00")
        fd = os.open(str(lock_path), os.O_RDWR)
        try:
            os.lseek(fd, 0, 0)
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                os.lseek(fd, 0, 0)
                _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)

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
