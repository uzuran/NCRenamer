"""PartStorageViewModel — mediator between PartStorageRepository and the UI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.models.part_storage_repository import PartStorageRepository


class PartStorageViewModel:
    """Exposes CRUD and search on leftover part records to the view layer."""

    def __init__(
        self, repo: PartStorageRepository, texts: dict | None = None
    ) -> None:
        self.repo = repo
        self.texts = texts or {}
        self._subscribers: list = []
        self._confirm_duplicate: Callable[[str], bool] | None = None

    # ------------------------------------------------------------------
    # Subscriber pattern
    # ------------------------------------------------------------------

    def subscribe(self, callback) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback) -> None:
        self._subscribers = [c for c in self._subscribers if c != callback]

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            try:
                cb()
            except Exception:
                pass

    def update_texts(self, texts: dict) -> None:
        self.texts = texts or {}

    def set_confirm_duplicate(self, callback: Callable[[str], bool]) -> None:
        """Register the View's confirmation dialog for duplicate part numbers.

        The callback receives the duplicate part_number and must return True
        to allow adding anyway, or False to cancel.  When no callback is
        registered every duplicate is silently rejected.
        """
        self._confirm_duplicate = callback

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all_parts(self, query: str = "") -> list[dict]:
        """Return all parts, optionally filtered by partial part_number match."""
        query = query.strip()
        if query:
            return self.repo.search_by_part_number(query)
        return self.repo.load_parts()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_part(
        self, part_number: str, location: str, notes: str = ""
    ) -> tuple[bool, str]:
        part_number = part_number.strip()
        location = location.strip()
        if not part_number:
            return False, self.texts.get(
                "part_number_empty", "Part number cannot be empty."
            )
        if not location:
            return False, self.texts.get(
                "part_location_empty", "Location cannot be empty."
            )
        existing = self.repo.load_parts()
        is_duplicate = any(p["part_number"] == part_number for p in existing)
        if is_duplicate:
            if self._confirm_duplicate is None or not self._confirm_duplicate(
                part_number
            ):
                return False, self.texts.get(
                    "part_exists", "Part number already exists."
                )
        part_id = self.repo.add_part(part_number, location, notes=notes)
        if part_id is None:
            return False, self.texts.get(
                "part_number_empty", "Part number cannot be empty."
            )
        self._notify()
        return True, self.texts.get("part_added", "Part added.")

    def update_part(
        self, part_id: str, part_number: str, location: str, notes: str = ""
    ) -> tuple[bool, str]:
        part_number = part_number.strip()
        location = location.strip()
        if not part_number:
            return False, self.texts.get(
                "part_number_empty", "Part number cannot be empty."
            )
        if not location:
            return False, self.texts.get(
                "part_location_empty", "Location cannot be empty."
            )
        success = self.repo.update_part(part_id, part_number, location, notes)
        if not success:
            return False, self.texts.get("part_not_found", "Part not found.")
        self._notify()
        return True, self.texts.get("part_updated", "Part updated.")

    def delete_part(self, part_id: str) -> tuple[bool, str]:
        if not part_id:
            return False, self.texts.get("part_no_selected", "No part selected.")
        success = self.repo.delete_part(part_id)
        if not success:
            return False, self.texts.get("part_not_found", "Part not found.")
        self._notify()
        return True, self.texts.get("part_deleted", "Part deleted.")
