"""Unit tests for TodoViewModel — message strings, sorting, and delegation."""

from unittest.mock import MagicMock

from app.viewmodels.todo_view_model import TodoViewModel


def _make_vm(items=None, texts=None) -> tuple[TodoViewModel, MagicMock]:
    repo = MagicMock()
    repo.load_items.return_value = items or []
    repo.add_item.return_value = "fake-uuid"
    repo.update_item.return_value = True
    repo.toggle_done.return_value = True
    repo.delete_item.return_value = True
    vm = TodoViewModel(repo=repo, texts=texts or {})
    return vm, repo


# ── get_items ────────────────────────────────────────────────────────────────


class TestGetItems:
    def test_pending_items_sort_before_done(self):
        vm, _ = _make_vm(
            items=[
                {"id": "1", "text": "Done task", "done": True},
                {"id": "2", "text": "Pending task", "done": False},
            ]
        )
        result = vm.get_items()
        assert result[0]["text"] == "Pending task"
        assert result[1]["text"] == "Done task"

    def test_returns_empty_list_when_no_items(self):
        vm, _ = _make_vm()
        assert vm.get_items() == []

    def test_delegates_to_repo(self):
        vm, repo = _make_vm()
        vm.get_items()
        repo.load_items.assert_called_once()


# ── add_item ─────────────────────────────────────────────────────────────────


class TestAddItem:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"todo_added": "Task added."})
        ok, msg = vm.add_item("New task")
        assert ok is True
        assert msg == "Task added."

    def test_empty_text_returns_false(self):
        vm, _ = _make_vm(texts={"todo_empty": "Task cannot be empty."})
        ok, msg = vm.add_item("")
        assert ok is False
        assert msg == "Task cannot be empty."

    def test_whitespace_only_returns_false(self):
        vm, _ = _make_vm()
        ok, _ = vm.add_item("   ")
        assert ok is False

    def test_delegates_stripped_text_to_repo(self):
        vm, repo = _make_vm()
        vm.add_item("  task  ")
        repo.add_item.assert_called_once_with("task")

    def test_repo_returning_none_returns_false(self):
        vm, repo = _make_vm(texts={"todo_empty": "Task cannot be empty."})
        repo.add_item.return_value = None
        ok, msg = vm.add_item("something")
        assert ok is False
        assert msg == "Task cannot be empty."


# ── update_item ──────────────────────────────────────────────────────────────


class TestUpdateItem:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"todo_updated": "Task updated."})
        ok, msg = vm.update_item("some-id", "New text")
        assert ok is True
        assert msg == "Task updated."

    def test_empty_text_returns_false(self):
        vm, _ = _make_vm(texts={"todo_empty": "Task cannot be empty."})
        ok, msg = vm.update_item("some-id", "")
        assert ok is False
        assert msg == "Task cannot be empty."

    def test_not_found_returns_false(self):
        vm, repo = _make_vm(texts={"todo_not_found": "Task not found."})
        repo.update_item.return_value = False
        ok, msg = vm.update_item("bad-id", "text")
        assert ok is False
        assert msg == "Task not found."


# ── toggle_done ──────────────────────────────────────────────────────────────


class TestToggleDone:
    def test_marking_done_returns_done_message(self):
        vm, repo = _make_vm(texts={"todo_toggled_done": "Marked as done."})
        repo.toggle_done.return_value = True
        ok, msg = vm.toggle_done("some-id")
        assert ok is True
        assert msg == "Marked as done."

    def test_marking_pending_returns_pending_message(self):
        vm, repo = _make_vm(texts={"todo_toggled_pending": "Marked as pending."})
        repo.toggle_done.return_value = False
        ok, msg = vm.toggle_done("some-id")
        assert ok is True
        assert msg == "Marked as pending."

    def test_not_found_returns_false(self):
        vm, repo = _make_vm(texts={"todo_not_found": "Task not found."})
        repo.toggle_done.return_value = None
        ok, msg = vm.toggle_done("bad-id")
        assert ok is False
        assert msg == "Task not found."


# ── delete_item ──────────────────────────────────────────────────────────────


class TestDeleteItem:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"todo_deleted": "Task deleted."})
        ok, msg = vm.delete_item("some-id")
        assert ok is True
        assert msg == "Task deleted."

    def test_empty_id_returns_false(self):
        vm, _ = _make_vm(texts={"todo_no_selected": "No task selected."})
        ok, msg = vm.delete_item("")
        assert ok is False
        assert msg == "No task selected."

    def test_not_found_returns_false(self):
        vm, repo = _make_vm(texts={"todo_not_found": "Task not found."})
        repo.delete_item.return_value = False
        ok, msg = vm.delete_item("bad-id")
        assert ok is False
        assert msg == "Task not found."


# ── update_texts ─────────────────────────────────────────────────────────────


class TestUpdateTexts:
    def test_replaces_texts_dict(self):
        vm, _ = _make_vm(texts={"todo_added": "Task added."})
        vm.update_texts({"todo_added": "Added!"})
        ok, msg = vm.add_item("x")
        assert msg == "Added!"

    def test_none_is_treated_as_empty_dict(self):
        vm, _ = _make_vm()
        vm.update_texts(None)
        assert vm.texts == {}
