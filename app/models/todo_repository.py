"""Shared todo-item repository backed by a single JSON file.

Follows the same pattern as MaterialRepository: atomic writes, OS-level
file locking, and path resolved from sys.argv[0] so the same file is
used regardless of which shortcut or path launched the application.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from app.utils.shared_storage import exe_dir as _exe_dir, file_lock as _file_lock


class TodoRepository:
    """CRUD interface for a list of todo items stored in JSON."""

    _LOCK_FILENAME = "todo.lock"
    _DEFAULT_SUBDIR = Path("todo")
    _DEFAULT_FILENAME = "todo.json"

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
                    if isinstance(item, dict) and "id" in item and "text" in item
                ]
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_items(self) -> list[dict]:
        """Return all items as a list of dicts with keys id, text, done."""
        with _file_lock(self._lock_path):
            return self._read()

    def add_item(self, text: str) -> str | None:
        """Append a new item. Returns the new item's id, or None if text is empty."""
        text = text.strip()
        if not text:
            return None
        item_id = str(uuid.uuid4())
        with _file_lock(self._lock_path):
            data = self._read()
            data.append({"id": item_id, "text": text, "done": False})
            self._write_atomic(data)
        return item_id

    def update_item(self, item_id: str, text: str) -> bool:
        """Update the text of an item. Returns False if the id is not found."""
        text = text.strip()
        if not text:
            return False
        with _file_lock(self._lock_path):
            data = self._read()
            for item in data:
                if item["id"] == item_id:
                    item["text"] = text
                    self._write_atomic(data)
                    return True
        return False

    def toggle_done(self, item_id: str) -> bool | None:
        """Flip the done flag. Returns new done value, or None if not found."""
        with _file_lock(self._lock_path):
            data = self._read()
            for item in data:
                if item["id"] == item_id:
                    item["done"] = not item.get("done", False)
                    self._write_atomic(data)
                    return item["done"]
        return None

    def delete_item(self, item_id: str) -> bool:
        """Delete an item. Returns False if the id is not found."""
        with _file_lock(self._lock_path):
            data = self._read()
            new_data = [item for item in data if item["id"] != item_id]
            if len(new_data) == len(data):
                return False
            self._write_atomic(new_data)
        return True
