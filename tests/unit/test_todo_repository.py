"""Unit tests for TodoRepository — CRUD, persistence, and error handling."""

import json
from pathlib import Path

import pytest

from app.models.todo_repository import TodoRepository


@pytest.fixture
def repo(tmp_path: Path) -> TodoRepository:
    return TodoRepository(path=tmp_path / "todo.json")


# ── add_item ─────────────────────────────────────────────────────────────────


class TestAddItem:
    def test_returns_id_string(self, repo):
        item_id = repo.add_item("Buy milk")
        assert isinstance(item_id, str) and item_id

    def test_empty_text_returns_none(self, repo):
        assert repo.add_item("") is None

    def test_whitespace_only_returns_none(self, repo):
        assert repo.add_item("   ") is None

    def test_item_appears_in_load(self, repo):
        repo.add_item("Buy milk")
        items = repo.load_items()
        assert len(items) == 1
        assert items[0]["text"] == "Buy milk"

    def test_item_starts_not_done(self, repo):
        repo.add_item("Do laundry")
        assert repo.load_items()[0]["done"] is False

    def test_text_is_stripped(self, repo):
        repo.add_item("  task  ")
        assert repo.load_items()[0]["text"] == "task"

    def test_created_at_is_stored(self, repo):
        repo.add_item("Check created_at")
        item = repo.load_items()[0]
        assert "created_at" in item
        assert item["created_at"]  # non-empty

    def test_created_at_format(self, repo):
        repo.add_item("Format check")
        raw = repo.load_items()[0]["created_at"]
        # expect "YYYY-MM-DD HH:MM"
        parts = raw.split()
        assert len(parts) == 2
        date_parts = parts[0].split("-")
        assert len(date_parts) == 3
        assert len(date_parts[0]) == 4  # year

    def test_multiple_items_accumulate(self, repo):
        repo.add_item("First")
        repo.add_item("Second")
        assert len(repo.load_items()) == 2


# ── load_items ───────────────────────────────────────────────────────────────


class TestLoadItems:
    def test_empty_on_fresh_repo(self, repo):
        assert repo.load_items() == []

    def test_skips_items_without_id(self, tmp_path):
        path = tmp_path / "todo.json"
        path.write_text(json.dumps([{"text": "no id here"}]), encoding="utf-8")
        r = TodoRepository(path=path)
        assert r.load_items() == []

    def test_skips_items_without_text(self, tmp_path):
        path = tmp_path / "todo.json"
        path.write_text(json.dumps([{"id": "abc", "done": False}]), encoding="utf-8")
        r = TodoRepository(path=path)
        assert r.load_items() == []

    def test_returns_empty_on_corrupt_json(self, tmp_path):
        path = tmp_path / "todo.json"
        path.write_text("not json {{", encoding="utf-8")
        r = TodoRepository(path=path)
        assert r.load_items() == []


# ── update_item ──────────────────────────────────────────────────────────────


class TestUpdateItem:
    def test_updates_existing_item(self, repo):
        item_id = repo.add_item("Old text")
        assert repo.update_item(item_id, "New text") is True
        assert repo.load_items()[0]["text"] == "New text"

    def test_returns_false_for_unknown_id(self, repo):
        assert repo.update_item("nonexistent", "text") is False

    def test_returns_false_for_empty_text(self, repo):
        item_id = repo.add_item("Task")
        assert repo.update_item(item_id, "") is False

    def test_text_is_stripped_on_update(self, repo):
        item_id = repo.add_item("Task")
        repo.update_item(item_id, "  updated  ")
        assert repo.load_items()[0]["text"] == "updated"


# ── toggle_done ──────────────────────────────────────────────────────────────


class TestToggleDone:
    def test_flips_false_to_true(self, repo):
        item_id = repo.add_item("Task")
        result = repo.toggle_done(item_id)
        assert result is True

    def test_flips_true_to_false(self, repo):
        item_id = repo.add_item("Task")
        repo.toggle_done(item_id)
        result = repo.toggle_done(item_id)
        assert result is False

    def test_returns_none_for_unknown_id(self, repo):
        assert repo.toggle_done("nonexistent") is None

    def test_done_flag_persisted(self, repo):
        item_id = repo.add_item("Task")
        repo.toggle_done(item_id)
        assert repo.load_items()[0]["done"] is True


# ── delete_item ──────────────────────────────────────────────────────────────


class TestDeleteItem:
    def test_removes_existing_item(self, repo):
        item_id = repo.add_item("Task")
        assert repo.delete_item(item_id) is True
        assert repo.load_items() == []

    def test_returns_false_for_unknown_id(self, repo):
        assert repo.delete_item("nonexistent") is False

    def test_other_items_unaffected(self, repo):
        repo.add_item("Keep")
        item_id = repo.add_item("Delete me")
        repo.delete_item(item_id)
        items = repo.load_items()
        assert len(items) == 1
        assert items[0]["text"] == "Keep"


# ── persistence ──────────────────────────────────────────────────────────────


class TestPersistence:
    def test_data_survives_new_instance(self, tmp_path):
        path = tmp_path / "todo.json"
        r1 = TodoRepository(path=path)
        r1.add_item("Persistent task")

        r2 = TodoRepository(path=path)
        items = r2.load_items()
        assert len(items) == 1
        assert items[0]["text"] == "Persistent task"
