"""Unit tests for PartStorageViewModel — messages, delegation, duplicate guard."""

from unittest.mock import MagicMock

from app.viewmodels.part_storage_view_model import PartStorageViewModel


def _make_vm(parts=None, texts=None) -> tuple[PartStorageViewModel, MagicMock]:
    repo = MagicMock()
    repo.load_parts.return_value = parts or []
    repo.add_part.return_value = "fake-uuid"
    repo.update_part.return_value = True
    repo.delete_part.return_value = True
    repo.search_by_part_number.return_value = parts or []
    vm = PartStorageViewModel(repo=repo, texts=texts or {})
    return vm, repo


# ── get_all_parts ─────────────────────────────────────────────────────────────


class TestGetAllParts:
    def test_no_query_delegates_to_load_parts(self):
        vm, repo = _make_vm()
        vm.get_all_parts()
        repo.load_parts.assert_called_once()
        repo.search_by_part_number.assert_not_called()

    def test_with_query_delegates_to_search(self):
        vm, repo = _make_vm()
        vm.get_all_parts("ABC")
        repo.search_by_part_number.assert_called_once_with("ABC")
        repo.load_parts.assert_not_called()

    def test_whitespace_query_uses_load_parts(self):
        vm, repo = _make_vm()
        vm.get_all_parts("   ")
        repo.load_parts.assert_called_once()

    def test_returns_empty_list_when_no_parts(self):
        vm, _ = _make_vm()
        assert vm.get_all_parts() == []


# ── add_part ──────────────────────────────────────────────────────────────────


class TestAddPart:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"part_added": "Part added."})
        ok, msg = vm.add_part("ABC-001", "Regal A3")
        assert ok is True
        assert msg == "Part added."

    def test_empty_part_number_returns_false(self):
        vm, _ = _make_vm(texts={"part_number_empty": "Part number cannot be empty."})
        ok, msg = vm.add_part("", "Regal A3")
        assert ok is False
        assert msg == "Part number cannot be empty."

    def test_whitespace_part_number_returns_false(self):
        vm, _ = _make_vm()
        ok, _ = vm.add_part("   ", "Regal A3")
        assert ok is False

    def test_empty_location_returns_false(self):
        vm, _ = _make_vm(texts={"part_location_empty": "Location cannot be empty."})
        ok, msg = vm.add_part("ABC-001", "")
        assert ok is False
        assert msg == "Location cannot be empty."

    def test_delegates_stripped_values_to_repo(self):
        vm, repo = _make_vm()
        vm.add_part("  ABC-001  ", "  Regal A3  ")
        repo.add_part.assert_called_once_with("ABC-001", "Regal A3", notes="")

    def test_notes_passed_to_repo(self):
        vm, repo = _make_vm()
        vm.add_part("ABC-001", "Regal A3", notes="some note")
        repo.add_part.assert_called_once_with("ABC-001", "Regal A3", notes="some note")

    def test_repo_returning_none_returns_false(self):
        vm, repo = _make_vm(texts={"part_number_empty": "Part number cannot be empty."})
        repo.add_part.return_value = None
        ok, msg = vm.add_part("ABC-001", "Regal A3")
        assert ok is False

    def test_notifies_on_success(self):
        vm, _ = _make_vm()
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.add_part("ABC-001", "Regal A3")
        assert len(called) == 1

    def test_no_notify_on_failure(self):
        vm, _ = _make_vm()
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.add_part("", "Regal A3")
        assert called == []


# ── duplicate handling ────────────────────────────────────────────────────────


class TestDuplicateHandling:
    def _vm_with_existing(self, part_number: str):
        existing = [{"id": "x", "part_number": part_number, "location": "A1"}]
        vm, repo = _make_vm(parts=existing)
        return vm, repo

    def test_rejected_when_no_callback_registered(self):
        vm, _ = self._vm_with_existing("ABC-001")
        ok, _ = vm.add_part("ABC-001", "Regal B2")
        assert ok is False

    def test_rejected_when_callback_returns_false(self):
        vm, _ = self._vm_with_existing("ABC-001")
        vm.set_confirm_duplicate(lambda pn: False)
        ok, _ = vm.add_part("ABC-001", "Regal B2")
        assert ok is False

    def test_allowed_when_callback_returns_true(self):
        vm, _ = self._vm_with_existing("ABC-001")
        vm.set_confirm_duplicate(lambda pn: True)
        ok, _ = vm.add_part("ABC-001", "Regal B2")
        assert ok is True

    def test_callback_receives_part_number(self):
        vm, _ = self._vm_with_existing("ABC-001")
        received = []
        vm.set_confirm_duplicate(lambda pn: received.append(pn) or True)
        vm.add_part("ABC-001", "Regal B2")
        assert received == ["ABC-001"]

    def test_exists_message_used_on_rejection(self):
        vm, _ = self._vm_with_existing("ABC-001")
        vm, _ = _make_vm(
            parts=[{"id": "x", "part_number": "ABC-001", "location": "A1"}],
            texts={"part_exists": "Part number already exists."},
        )
        ok, msg = vm.add_part("ABC-001", "Regal B2")
        assert ok is False
        assert msg == "Part number already exists."

    def test_unique_part_number_skips_duplicate_check(self):
        vm, repo = _make_vm(parts=[])
        called = []
        vm.set_confirm_duplicate(lambda pn: called.append(pn) or False)
        vm.add_part("NEW-999", "Regal X1")
        assert called == []


# ── update_part ───────────────────────────────────────────────────────────────


class TestUpdatePart:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"part_updated": "Part updated."})
        ok, msg = vm.update_part("some-id", "ABC-002", "Regal B1")
        assert ok is True
        assert msg == "Part updated."

    def test_empty_part_number_returns_false(self):
        vm, _ = _make_vm(texts={"part_number_empty": "Part number cannot be empty."})
        ok, msg = vm.update_part("some-id", "", "Regal A3")
        assert ok is False
        assert msg == "Part number cannot be empty."

    def test_empty_location_returns_false(self):
        vm, _ = _make_vm(texts={"part_location_empty": "Location cannot be empty."})
        ok, msg = vm.update_part("some-id", "ABC-001", "")
        assert ok is False
        assert msg == "Location cannot be empty."

    def test_not_found_returns_false(self):
        vm, repo = _make_vm(texts={"part_not_found": "Part not found."})
        repo.update_part.return_value = False
        ok, msg = vm.update_part("bad-id", "ABC-001", "Regal A3")
        assert ok is False
        assert msg == "Part not found."

    def test_notifies_on_success(self):
        vm, _ = _make_vm()
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.update_part("some-id", "ABC-001", "Regal A3")
        assert len(called) == 1

    def test_no_notify_on_failure(self):
        vm, repo = _make_vm()
        repo.update_part.return_value = False
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.update_part("bad-id", "ABC-001", "Regal A3")
        assert called == []


# ── delete_part ───────────────────────────────────────────────────────────────


class TestDeletePart:
    def test_success_returns_true_and_message(self):
        vm, _ = _make_vm(texts={"part_deleted": "Part deleted."})
        ok, msg = vm.delete_part("some-id")
        assert ok is True
        assert msg == "Part deleted."

    def test_empty_id_returns_false(self):
        vm, _ = _make_vm(texts={"part_no_selected": "No part selected."})
        ok, msg = vm.delete_part("")
        assert ok is False
        assert msg == "No part selected."

    def test_not_found_returns_false(self):
        vm, repo = _make_vm(texts={"part_not_found": "Part not found."})
        repo.delete_part.return_value = False
        ok, msg = vm.delete_part("bad-id")
        assert ok is False
        assert msg == "Part not found."

    def test_notifies_on_success(self):
        vm, _ = _make_vm()
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.delete_part("some-id")
        assert len(called) == 1

    def test_no_notify_on_failure(self):
        vm, repo = _make_vm()
        repo.delete_part.return_value = False
        called = []
        vm.subscribe(lambda: called.append(1))
        vm.delete_part("bad-id")
        assert called == []


# ── update_texts ──────────────────────────────────────────────────────────────


class TestUpdateTexts:
    def test_replaces_texts_dict(self):
        vm, _ = _make_vm(texts={"part_added": "Part added."})
        vm.update_texts({"part_added": "Added!"})
        ok, msg = vm.add_part("ABC-001", "Regal A3")
        assert msg == "Added!"

    def test_none_treated_as_empty_dict(self):
        vm, _ = _make_vm()
        vm.update_texts(None)
        assert vm.texts == {}
