"""Tests for MaterialsViewModel subscriber / auto-refresh callbacks.

MaterialsFrame and AddMaterialFrame share ONE MaterialsViewModel instance
(see app.py), so both frames register a subscriber on the same VM object.
These tests verify that _notify() fires to all subscribers on every
successful mutation and is silent on validation failures.
"""

from tests.conftest import StubMaterialRepository
from app.viewmodels.materials_view_model import MaterialsViewModel


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_vm(materials=None) -> MaterialsViewModel:
    repo = StubMaterialRepository(materials or [])
    return MaterialsViewModel(app_instance=None, repo=repo, texts={
        "no_empty": "empty",
        "material_exists": "exists",
        "material_added": "added",
        "material_updated": "updated",
        "no_material_selected": "none",
        "material_not_found": "not found",
        "material_removed": "removed",
    })


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
        vm.unsubscribe(lambda: None)

    def test_multiple_subscribers_all_called(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm._notify()
        assert a.calls[0] == 1 and b.calls[0] == 1

    def test_no_subscribers_notify_does_not_raise(self):
        vm = _make_vm()
        vm._notify()


# ══════════════════════════════════════════════════════════════════════════════
# 2. add_material
# ══════════════════════════════════════════════════════════════════════════════


class TestAddMaterialNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_material("WRONG", "RIGHT")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_incorrect(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_material("", "RIGHT")
        assert cb.calls[0] == 0

    def test_no_callback_on_empty_correct(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.add_material("WRONG", "")
        assert cb.calls[0] == 0

    def test_no_callback_on_duplicate(self):
        vm = _make_vm([["WRONG", "RIGHT"]])
        cb = _counter()
        vm.subscribe(cb)
        vm.add_material("WRONG", "OTHER")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. update_material
# ══════════════════════════════════════════════════════════════════════════════


class TestUpdateMaterialNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm([["WRONG", "RIGHT"]])
        cb = _counter()
        vm.subscribe(cb)
        vm.update_material("WRONG", "WRONG2", "RIGHT2")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_fields(self):
        vm = _make_vm([["WRONG", "RIGHT"]])
        cb = _counter()
        vm.subscribe(cb)
        vm.update_material("", "", "")
        assert cb.calls[0] == 0

    def test_no_callback_when_not_found(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.update_material("NONEXISTENT", "X", "Y")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. remove_material
# ══════════════════════════════════════════════════════════════════════════════


class TestRemoveMaterialNotifies:
    def test_fires_callback_on_success(self):
        vm = _make_vm([["WRONG", "RIGHT"]])
        cb = _counter()
        vm.subscribe(cb)
        vm.remove_material("WRONG")
        assert cb.calls[0] == 1

    def test_no_callback_on_empty_incorrect(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.remove_material("")
        assert cb.calls[0] == 0

    def test_no_callback_when_not_found(self):
        vm = _make_vm()
        cb = _counter()
        vm.subscribe(cb)
        vm.remove_material("NONEXISTENT")
        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 5. Multiple subscribers — simulates MaterialsFrame + AddMaterialFrame
# ══════════════════════════════════════════════════════════════════════════════


class TestMultipleSubscribers:
    def test_both_frames_notified_on_add(self):
        vm = _make_vm()
        materials_frame_refresh = _counter()
        add_material_frame_refresh = _counter()
        vm.subscribe(materials_frame_refresh)
        vm.subscribe(add_material_frame_refresh)
        vm.add_material("A", "B")
        assert materials_frame_refresh.calls[0] == 1
        assert add_material_frame_refresh.calls[0] == 1

    def test_both_frames_notified_on_remove(self):
        vm = _make_vm([["A", "B"]])
        materials_frame_refresh = _counter()
        add_material_frame_refresh = _counter()
        vm.subscribe(materials_frame_refresh)
        vm.subscribe(add_material_frame_refresh)
        vm.remove_material("A")
        assert materials_frame_refresh.calls[0] == 1
        assert add_material_frame_refresh.calls[0] == 1

    def test_both_frames_notified_on_update(self):
        vm = _make_vm([["A", "B"]])
        materials_frame_refresh = _counter()
        add_material_frame_refresh = _counter()
        vm.subscribe(materials_frame_refresh)
        vm.subscribe(add_material_frame_refresh)
        vm.update_material("A", "A2", "B2")
        assert materials_frame_refresh.calls[0] == 1
        assert add_material_frame_refresh.calls[0] == 1

    def test_unsubscribed_frame_not_called(self):
        vm = _make_vm()
        a, b = _counter(), _counter()
        vm.subscribe(a)
        vm.subscribe(b)
        vm.unsubscribe(a)
        vm.add_material("X", "Y")
        assert a.calls[0] == 0
        assert b.calls[0] == 1
