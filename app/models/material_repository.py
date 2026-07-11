"""Shared material repository backed by a single JSON file.

Path resolution
---------------
The JSON file lives in ``<exe_dir>/materials/materials.json`` where
``exe_dir`` is the directory that contains the main executable (or entry
script when running from source).  Resolving from ``sys.argv[0]`` — not
from the current working directory or ``__file__`` — means the path is
always the same regardless of whether the user launches the program from a
shortcut, a network path, or a mapped drive.

Concurrency safety
------------------
Every read/write operation acquires an exclusive OS-level lock on a
``materials.lock`` file next to the JSON file.  On Windows ``msvcrt``
(standard library) is used; on POSIX ``fcntl`` (standard library) is used.
No third-party locking library is required.

Atomic writes
-------------
Data is first written to ``materials.tmp`` then renamed over the real file
with ``os.replace()``.  On POSIX this is a single syscall and is atomic; on
Windows ``os.replace()`` is atomic within the same volume.  A crash between
the two steps leaves the old file intact.

Migration
---------
If the shared JSON does not exist yet the repository checks the old per-user
CSV location (``%APPDATA%/Local/NCRenamer/materials_new.csv``) and imports
any data it finds there, so existing users keep their mappings.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _exe_dir() -> Path:
    """Return the directory of the running executable / entry script.

    - ``python app.py``  →  parent of *app.py*
    - PyInstaller EXE (incl. via shortcut)  →  parent of the real *.exe*
      because ``sys.argv[0]`` always reflects the physical executable path,
      not the shortcut that launched it.
    """
    return Path(sys.argv[0]).resolve().parent


# ---------------------------------------------------------------------------
# Platform file locking
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import msvcrt as _msvcrt

    @contextlib.contextmanager
    def _file_lock(lock_path: Path):
        """Exclusive blocking lock using msvcrt (Windows only)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        # The lock file must contain at least one byte for msvcrt.locking.
        if not lock_path.exists():
            lock_path.write_bytes(b"\x00")
        fd = os.open(str(lock_path), os.O_RDWR)
        try:
            os.lseek(fd, 0, 0)
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)  # retries for ~10 s
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
    def _file_lock(lock_path: Path):
        """Exclusive blocking lock using fcntl (POSIX)."""
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "a") as _f:
            _fcntl.flock(_f, _fcntl.LOCK_EX)
            try:
                yield
            finally:
                _fcntl.flock(_f, _fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class MaterialRepository:
    """CRUD interface for the shared material-mapping store."""

    _LOCK_FILENAME = "materials.lock"
    _DEFAULT_SUBDIR = Path("materials")
    _DEFAULT_FILENAME = "materials.json"

    def __init__(self, path: Path | None = None) -> None:
        """
        Parameters
        ----------
        path:
            Override the resolved path — intended for tests only.
            When *None* the path is resolved from ``sys.argv[0]``.
        """
        if path is not None:
            self._path = path
        else:
            self._path = _exe_dir() / self._DEFAULT_SUBDIR / self._DEFAULT_FILENAME

        self._lock_path = self._path.parent / self._LOCK_FILENAME
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    # ------------------------------------------------------------------
    # Internal helpers (no locking — callers hold the lock)
    # ------------------------------------------------------------------

    def _ensure_file_exists(self) -> None:
        if self._path.exists():
            return
        with _file_lock(self._lock_path):
            if self._path.exists():  # another process may have created it
                return
            if not self._migrate_from_csv():
                self._write_atomic([])

    def _migrate_from_csv(self) -> bool:
        """Import data from the old per-user CSV if it exists. Returns True on success."""
        import csv

        candidates = [
            Path.home() / "AppData" / "Local" / "NCRenamer" / "materials_new.csv",
        ]
        for csv_path in candidates:
            if not csv_path.exists():
                continue
            try:
                with open(csv_path, encoding="utf-8-sig") as f:
                    rows = [row for row in csv.reader(f, delimiter="\t") if len(row) >= 2]
                if rows:
                    self._write_atomic(rows)
                    return True
            except Exception:
                pass
        return False

    def _write_atomic(self, data: list[list[str]]) -> None:
        """Write *data* to a temp file then atomically rename it over the real file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self._path)

    def _read(self) -> list[list[str]]:
        """Read and parse the JSON file; return [] on any error."""
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [row for row in data if isinstance(row, list) and len(row) >= 2]
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Public CRUD API
    # ------------------------------------------------------------------

    def load_materials(self) -> list[list[str]]:
        """Return all material mappings as a list of ``[incorrect, correct]`` pairs."""
        with _file_lock(self._lock_path):
            return self._read()

    def add_material(self, incorrect: str, correct: str) -> bool:
        """Append a new mapping.  Returns *False* if *incorrect* already exists."""
        incorrect = incorrect.strip()
        correct = correct.strip()
        with _file_lock(self._lock_path):
            data = self._read()
            if any(row[0] == incorrect for row in data):
                return False
            data.append([incorrect, correct])
            self._write_atomic(data)
        return True

    def update_material(
        self, incorrect: str, new_incorrect: str, new_correct: str
    ) -> bool:
        """Update an existing mapping.  Returns *False* if *incorrect* is not found."""
        incorrect = incorrect.strip()
        new_incorrect = new_incorrect.strip()
        new_correct = new_correct.strip()
        with _file_lock(self._lock_path):
            data = self._read()
            for row in data:
                if row[0].strip() == incorrect:
                    row[0] = new_incorrect
                    row[1] = new_correct
                    self._write_atomic(data)
                    return True
        return False

    def delete_material(self, incorrect: str) -> bool:
        """Delete a mapping.  Returns *False* if *incorrect* is not found."""
        incorrect = incorrect.strip()
        with _file_lock(self._lock_path):
            data = self._read()
            new_data = [row for row in data if row[0].strip() != incorrect]
            if len(new_data) == len(data):
                return False
            self._write_atomic(new_data)
        return True
