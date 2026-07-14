"""TodoViewModel — mediator between TodoRepository and the todo UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.todo_repository import TodoRepository


class TodoViewModel:
    """Exposes CRUD operations on todo items to the view layer."""

    def __init__(self, repo: TodoRepository, texts: dict | None = None) -> None:
        self.repo = repo
        self.texts = texts or {}
        self._subscribers: list = []

    def subscribe(self, callback) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback) -> None:
        self._subscribers = [c for c in self._subscribers if c != callback]

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def update_texts(self, texts: dict) -> None:
        self.texts = texts or {}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_items(self) -> list[dict]:
        """Return all items sorted: pending first, then done."""
        items = self.repo.load_items()
        return sorted(items, key=lambda i: i.get("done", False))

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add_item(self, text: str) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, self.texts.get("todo_empty", "Task cannot be empty.")
        item_id = self.repo.add_item(text)
        if item_id is None:
            return False, self.texts.get("todo_empty", "Task cannot be empty.")
        self._notify()
        return True, self.texts.get("todo_added", "Task added.")

    def update_item(self, item_id: str, text: str) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, self.texts.get("todo_empty", "Task cannot be empty.")
        success = self.repo.update_item(item_id, text)
        if not success:
            return False, self.texts.get("todo_not_found", "Task not found.")
        self._notify()
        return True, self.texts.get("todo_updated", "Task updated.")

    def toggle_done(self, item_id: str) -> tuple[bool, str]:
        new_done = self.repo.toggle_done(item_id)
        if new_done is None:
            return False, self.texts.get("todo_not_found", "Task not found.")
        self._notify()
        if new_done:
            return True, self.texts.get("todo_toggled_done", "Marked as done.")
        return True, self.texts.get("todo_toggled_pending", "Marked as pending.")

    def delete_item(self, item_id: str) -> tuple[bool, str]:
        if not item_id:
            return False, self.texts.get("todo_no_selected", "No task selected.")
        success = self.repo.delete_item(item_id)
        if not success:
            return False, self.texts.get("todo_not_found", "Task not found.")
        self._notify()
        return True, self.texts.get("todo_deleted", "Task deleted.")
