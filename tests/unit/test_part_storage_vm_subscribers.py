"""Tests for PartStorageViewModel subscriber mechanics."""

from unittest.mock import MagicMock

from app.viewmodels.part_storage_view_model import PartStorageViewModel


def _counter():
    calls = [0]

    def cb():
        calls[0] += 1

    cb.count = calls
    return cb


def _make_vm(parts=None):
    repo = MagicMock()
    repo.load_parts.return_value = parts or []
    repo.add_part.return_value = "fake-uuid"
    repo.update_part.return_value = True
    repo.delete_part.return_value = True
    return PartStorageViewModel(repo=repo), repo


# ── subscribe / unsubscribe / _notify ────────────────────────────────────────


class TestSubscriberMechanics:
    def test_subscribe_registers_callback(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm._notify()
        assert cb.count[0] == 1

    def test_duplicate_subscribe_is_noop(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.subscribe(cb)
        vm._notify()
        assert cb.count[0] == 1

    def test_unsubscribe_stops_notifications(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.unsubscribe(cb)
        vm._notify()
        assert cb.count[0] == 0

    def test_unsubscribe_unknown_callback_is_noop(self):
        vm, _ = _make_vm()
        vm.unsubscribe(lambda: None)  # must not raise

    def test_multiple_subscribers_all_notified(self):
        vm, _ = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm._notify()
        assert a.count[0] == 1
        assert b.count[0] == 1

    def test_broken_callback_does_not_crash_vm(self):
        vm, _ = _make_vm()
        vm.subscribe(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        vm._notify()  # must not raise

    def test_notify_iterates_snapshot(self):
        """Unsubscribing inside a callback must not skip the next subscriber."""
        vm, _ = _make_vm()
        a_calls, b_calls = [], []

        def a():
            a_calls.append(1)
            vm.unsubscribe(a)

        def b():
            b_calls.append(1)

        vm.subscribe(a)
        vm.subscribe(b)
        vm._notify()
        assert len(a_calls) == 1
        assert len(b_calls) == 1


# ── notify only fires on success ──────────────────────────────────────────────


class TestNotifyOnSuccess:
    def test_add_part_notifies_on_success(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_part("ABC-001", "Regal A3")
        assert cb.count[0] == 1

    def test_add_part_no_notify_on_empty_part_number(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_part("", "Regal A3")
        assert cb.count[0] == 0

    def test_add_part_no_notify_on_empty_location(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_part("ABC-001", "")
        assert cb.count[0] == 0

    def test_update_part_notifies_on_success(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.update_part("some-id", "ABC-001", "Regal A3")
        assert cb.count[0] == 1

    def test_update_part_no_notify_on_not_found(self):
        vm, repo = _make_vm()
        repo.update_part.return_value = False
        cb = _counter()
        vm.subscribe(cb)
        vm.update_part("bad-id", "ABC-001", "Regal A3")
        assert cb.count[0] == 0

    def test_delete_part_notifies_on_success(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_part("some-id")
        assert cb.count[0] == 1

    def test_delete_part_no_notify_on_not_found(self):
        vm, repo = _make_vm()
        repo.delete_part.return_value = False
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_part("bad-id")
        assert cb.count[0] == 0

    def test_delete_part_no_notify_on_empty_id(self):
        vm, _ = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_part("")
        assert cb.count[0] == 0
