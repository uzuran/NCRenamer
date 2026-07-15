"""Shared part-storage repository backed by a single JSON file.

Follows the same pattern as TodoRepository: atomic writes, OS-level file
locking, and path resolved from sys.argv[0] so the same file is used
regardless of which shortcut or path launched the application.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from pathlib import Path

from app.utils.shared_storage import exe_dir as _exe_dir
from app.utils.shared_storage import file_lock as _file_lock


class PartStorageRepository:
    """CRUD interface for leftover parts stored in a shared JSON file."""

    _LOCK_FILENAME = "part_storage.lock"
    _DEFAULT_SUBDIR = Path("shared")
    _DEFAULT_FILENAME = "part_storage.json"

    def __init__(self, path: Path | None = None) -> None:
        if path is not None:
            self._path = path
        else:
            self._path = _exe_dir() / self._DEFAULT_SUBDIR / self._DEFAULT_FILENAME

        self._lock_path = self._path.parent / self._LOCK_FILENAME
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_atomic([])

    # ------------------------------------------------------------------
    # Internal helpers (callers hold the lock)
    # ------------------------------------------------------------------

    def _write_atomic(self, data: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [
                    item
                    for item in data
                    if isinstance(item, dict)
                    and "id" in item
                    and "part_number" in item
                ]
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_parts(self) -> list[dict]:
        """Return all part records."""
        with _file_lock(self._lock_path):
            return self._read()

    def add_part(
        self,
        part_number: str,
        location: str,
        date_added: str = "",
        notes: str = "",
    ) -> str | None:
        """Append a new part record. Returns the new id, or None on validation error."""
        part_number = part_number.strip()
        location = location.strip()
        if not part_number or not location:
            return None
        part_id = str(uuid.uuid4())
        if not date_added:
            date_added = date.today().strftime("%Y-%m-%d")
        with _file_lock(self._lock_path):
            data = self._read()
            data.append(
                {
                    "id": part_id,
                    "part_number": part_number,
                    "location": location,
                    "date_added": date_added,
                    "notes": notes.strip(),
                }
            )
            self._write_atomic(data)
        return part_id

    def update_part(
        self,
        part_id: str,
        part_number: str,
        location: str,
        notes: str = "",
    ) -> bool:
        """Update a part record. Returns False if not found or validation fails."""
        part_number = part_number.strip()
        location = location.strip()
        if not part_number or not location:
            return False
        with _file_lock(self._lock_path):
            data = self._read()
            for item in data:
                if item["id"] == part_id:
                    item["part_number"] = part_number
                    item["location"] = location
                    item["notes"] = notes.strip()
                    self._write_atomic(data)
                    return True
        return False

    def delete_part(self, part_id: str) -> bool:
        """Delete a part record. Returns False if not found."""
        with _file_lock(self._lock_path):
            data = self._read()
            new_data = [item for item in data if item["id"] != part_id]
            if len(new_data) == len(data):
                return False
            self._write_atomic(new_data)
        return True

    def search_by_part_number(self, query: str) -> list[dict]:
        """Return parts whose part_number contains *query* (case-insensitive)."""
        query = query.strip().lower()
        with _file_lock(self._lock_path):
            data = self._read()
        if not query:
            return data
        return [
            item for item in data if query in item.get("part_number", "").lower()
        ]
