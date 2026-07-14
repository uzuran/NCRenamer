"""Tests for TodoViewModel subscriber / auto-refresh callbacks.

Verifies that _notify() fires to every registered subscriber after each
successful CRUD operation, and NOT after validation failures.
"""

from unittest.mock import MagicMock

import pytest

from app.viewmodels.todo_view_model import TodoViewModel


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_vm(*, add_returns="fake-id", update_returns=True,
             toggle_returns=True, delete_returns=True) -> TodoViewModel:
    repo = MagicMock()
    repo.add_item.return_value = add_returns
    repo.update_item.return_value = update_returns
    repo.toggle_done.return_value = toggle_returns
    repo.delete_item.return_value = delete_returns
    return TodoViewModel(repo=repo, texts={})


def _counter():
    calls = [0]
    def cb():
        calls[0] += 1
    cb.calls = calls
    return cb


# ══════════════════════════════════════════════════════════════════════════════
# 1. subscribe / unsubscribe
# ══════════════════════════════════════════════════════════════════════════════


class TestSubscribeUnsubscribe:
    def test_subscribe_registers_callback(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm._notify()
        assert cb.calls[0] == 1

    def test_subscribe_same_callback_twice_calls_once(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.subscribe(cb)
        vm._notify()
        assert cb.calls[0] == 1

    def test_unsubscribe_removes_callback(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.unsubscribe(cb)
        vm._notify()
        assert cb.calls[0] == 0

    def test_unsubscribe_nonexistent_does_not_raise(self):
        vm = _make_vm()
        vm.unsubscribe(lambda: None)  # should not raise

    def test_multiple_subscribers_all_called(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm._notify()
        assert a.calls[0] == 1
        assert b.calls[0] == 1

    def test_no_subscribers_notify_does_not_raise(self):
        vm = _make_vm()
        vm._notify()  # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 2. add_item
# ══════════════════════════════════════════════════════════════════════════════


class TestAddItemNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_item("Task text")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_text(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_item("")
        assert cb.calls[0] == 0

    def test_no_callback_on_whitespace_only(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_item("   ")
        assert cb.calls[0] == 0

    def test_no_callback_when_repo_returns_none(self):
        vm = _make_vm(add_returns=None)
        cb = _counter()
        vm.subscribe(cb)
        vm.add_item("Task text")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. update_item
# ══════════════════════════════════════════════════════════════════════════════


class TestUpdateItemNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.update_item("some-id", "Updated text")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_text(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.update_item("some-id", "")
        assert cb.calls[0] == 0

    def test_no_callback_when_not_found(self):
        vm = _make_vm(update_returns=False)
        cb = _counter()
        vm.subscribe(cb)
        vm.update_item("bad-id", "text")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. toggle_done
# ══════════════════════════════════════════════════════════════════════════════


class TestToggleDoneNotifies:
    def test_fires_callback_when_toggled_to_done(self):
        vm = _make_vm(toggle_returns=True)
        cb = _counter()
        vm.subscribe(cb)
        vm.toggle_done("some-id")
        assert cb.calls[0] == 1

    def test_fires_callback_when_toggled_to_pending(self):
        vm = _make_vm(toggle_returns=False)
        cb = _counter()
        vm.subscribe(cb)
        vm.toggle_done("some-id")
        assert cb.calls[0] == 1

    def test_no_callback_when_not_found(self):
        vm = _make_vm(toggle_returns=None)
        cb = _counter()
        vm.subscribe(cb)
        vm.toggle_done("bad-id")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. delete_item
# ══════════════════════════════════════════════════════════════════════════════


class TestDeleteItemNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_item("some-id")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_id(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_item("")
        assert cb.calls[0] == 0

    def test_no_callback_when_not_found(self):
        vm = _make_vm(delete_returns=False)
        cb = _counter()
        vm.subscribe(cb)
        vm.delete_item("bad-id")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 6. Multiple subscribers — all notified on each op
# ══════════════════════════════════════════════════════════════════════════════


class TestMultipleSubscribers:
    def test_two_subscribers_both_notified_on_add(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm.add_item("x")
        assert a.calls[0] == 1
        assert b.calls[0] == 1

    def test_two_subscribers_both_notified_on_delete(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm.delete_item("id")
        assert a.calls[0] == 1
        assert b.calls[0] == 1

    def test_unsubscribed_not_called_remaining_is(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm.unsubscribe(a)
        vm.add_item("x")
        assert a.calls[0] == 0
        assert b.calls[0] == 1
