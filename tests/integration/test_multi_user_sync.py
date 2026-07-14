"""Integration tests — real-time multi-user synchronisation via FileWatcher.

Tests the full chain:
  external file write → FileWatcher detects mtime change
                      → root.after(0, callback) fired
                      → view.reload_treeview() called
                      → fresh data visible

Each test uses a real FileWatcher polling thread with a short interval (50 ms)
and threading.Event to synchronise assertion timing.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.services.table_factory import TableFactory
from app.burn_table.viewmodels.burn_view_model import BurnViewModel
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder
from app.burn_table.viewmodels.print_manager import PrintManager
from app.models.material_repository import MaterialRepository
from app.models.todo_repository import TodoRepository
from app.utils.file_watcher import FileWatcher
from app.utils.workspace import WorkspaceManager


# ── helpers ───────────────────────────────────────────────────────────────────


class _SyncRoot:
    """Minimal tkinter root substitute: executes after() callbacks immediately."""

    def after(self, delay: int, callback) -> None:
        callback()


def _watcher(poll_ms: int = 50) -> FileWatcher:
    return FileWatcher(_SyncRoot(), poll_interval_ms=poll_ms)


def _wm(root: Path, *usernames: str) -> WorkspaceManager:
    wm = WorkspaceManager(root)
    wm.ensure_shared_workspace_exists()
    for u in usernames:
        wm.ensure_user_workspace_exists(u)
    return wm


def _burn_vm(path: Path | None = None, sheet_index: int = 0) -> BurnViewModel:
    vm = BurnViewModel(
        reader=ExcelReader(sheet_index=sheet_index),
        writer=ExcelWriter(sheet_index=sheet_index),
        detector=FreeSlotDetector(sheet_index=sheet_index),
        recorder=PerformanceRecorder(),
        print_manager=PrintManager(),
        sheet_name="Ocel" if sheet_index == 0 else "Hliník",
        settings_key="last_table_path",
    )
    if path is not None:
        vm.load_table(path)
    return vm


# ══════════════════════════════════════════════════════════════════════════════
# 1. Shared files — materials.json
# ══════════════════════════════════════════════════════════════════════════════


class TestMaterialsSync:
    def test_external_write_triggers_callback(self, tmp_path):
        """Writing to materials.json externally fires the registered callback."""
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        MaterialRepository(path=mat_path)  # creates file

        fired = threading.Event()
        fw = _watcher()
        fw.watch(mat_path, fired.set)
        fw.start()

        time.sleep(0.02)
        # Simulate User B writing to the shared file.
        mat_path.write_text(json.dumps([["WRONG", "RIGHT"]]), encoding="utf-8")

        assert fired.wait(timeout=2.0), "materials.json change not detected"
        fw.stop()

    def test_callback_not_fired_when_file_unchanged(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        MaterialRepository(path=mat_path)

        fired = threading.Event()
        fw = _watcher()
        fw.watch(mat_path, fired.set)
        fw.start()

        time.sleep(0.3)  # wait longer than one poll cycle
        assert not fired.is_set(), "Callback fired without a file change"
        fw.stop()

    def test_two_instances_both_see_material_change(self, tmp_path):
        """Simulate two app instances watching the same file."""
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        MaterialRepository(path=mat_path)

        reload_a = MagicMock()
        reload_b = MagicMock()
        evt = threading.Event()

        def _combined():
            reload_a()
            reload_b()
            evt.set()

        fw = _watcher()
        fw.watch(mat_path, _combined)
        fw.start()

        time.sleep(0.02)
        mat_path.write_text(json.dumps([["X", "Y"]]), encoding="utf-8")

        assert evt.wait(timeout=2.0)
        reload_a.assert_called_once()
        reload_b.assert_called_once()
        fw.stop()

    def test_acknowledge_write_suppresses_own_write(self, tmp_path):
        """Local (own) write acknowledged to the watcher must not re-trigger the callback."""
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        repo = MaterialRepository(path=mat_path)

        callback_count: list[int] = [0]
        fw = _watcher()

        def _on_change():
            callback_count[0] += 1

        fw.watch(mat_path, _on_change)
        fw.start()

        time.sleep(0.02)
        # Local write via repo — acknowledge immediately so watcher ignores it.
        repo.add_material("A", "B")
        fw.acknowledge_write(mat_path)

        time.sleep(0.2)  # allow two full poll cycles to pass
        assert callback_count[0] == 0, (
            f"Callback fired {callback_count[0]} times after local acknowledged write"
        )
        fw.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Shared files — todo.json
# ══════════════════════════════════════════════════════════════════════════════


class TestTodoSync:
    def test_external_write_triggers_callback(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        todo_path = wm.todo_path()
        TodoRepository(path=todo_path)

        fired = threading.Event()
        fw = _watcher()
        fw.watch(todo_path, fired.set)
        fw.start()

        time.sleep(0.02)
        todo_path.write_text(
            json.dumps([{"id": "1", "text": "Buy milk", "done": False}]),
            encoding="utf-8",
        )

        assert fired.wait(timeout=2.0), "todo.json change not detected"
        fw.stop()

    def test_callback_not_fired_when_unchanged(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        todo_path = wm.todo_path()
        TodoRepository(path=todo_path)

        fired = threading.Event()
        fw = _watcher()
        fw.watch(todo_path, fired.set)
        fw.start()

        time.sleep(0.3)
        assert not fired.is_set()
        fw.stop()

    def test_two_apps_share_todo_data(self, tmp_path):
        """Verify shared data model: User A writes, User B reads same file."""
        wm = _wm(tmp_path, "alice", "bob")
        todo_path = wm.todo_path()

        repo_a = TodoRepository(path=todo_path)
        repo_b = TodoRepository(path=todo_path)

        fired = threading.Event()
        fw = _watcher()
        fw.watch(todo_path, fired.set)
        fw.start()

        time.sleep(0.02)
        repo_a.add_item("Task from Alice")  # User A writes

        assert fired.wait(timeout=2.0), "Todo change not detected by watcher"

        items = repo_b.load_items()
        assert any(i["text"] == "Task from Alice" for i in items), (
            "User B did not see User A's new todo item"
        )
        fw.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 3. Per-user burn table
# ══════════════════════════════════════════════════════════════════════════════


class TestBurnTableSync:
    def test_external_write_triggers_callback(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        bt_path = wm.user_burn_table_path("alice")
        TableFactory().create(bt_path)

        fired = threading.Event()
        fw = _watcher()
        fw.watch(bt_path, fired.set)
        fw.start()

        time.sleep(0.02)
        # Simulate second instance appending a record.
        rec = BurnRecord(program_number="9999-01", sheet_format="1.0037-4X2000X1000", sheet_count=1)
        ExcelWriter().append_record(bt_path, rec)

        assert fired.wait(timeout=3.0), "burn_table.xlsx change not detected"
        fw.stop()

    def test_vm_reload_after_external_write(self, tmp_path):
        """After an external write, reload_treeview() via load_table() shows new record."""
        wm = _wm(tmp_path, "alice")
        bt_path = wm.user_burn_table_path("alice")
        TableFactory().create(bt_path)

        vm = _burn_vm(bt_path)
        assert len(vm._records) == 0

        # External write by another instance.
        rec = BurnRecord(program_number="9999-01", sheet_format="1.0037-4X2000X1000", sheet_count=1)
        ExcelWriter().append_record(bt_path, rec)

        # Simulate what burn_table_frame.reload_treeview() does.
        vm.load_table(bt_path)
        assert any(r.program_number == "9999-01" for r in vm._records)

    def test_per_user_isolation_maintained(self, tmp_path):
        """Watcher for alice's file must not fire when bob's file changes."""
        wm = _wm(tmp_path, "alice", "bob")
        alice_path = wm.user_burn_table_path("alice")
        bob_path = wm.user_burn_table_path("bob")
        TableFactory().create(alice_path)
        TableFactory().create(bob_path)

        alice_fired = threading.Event()
        bob_fired = threading.Event()

        fw = _watcher()
        fw.watch(alice_path, alice_fired.set)
        fw.watch(bob_path, bob_fired.set)
        fw.start()

        time.sleep(0.02)
        rec = BurnRecord(program_number="BOB-01", sheet_format="1.0037-4X2000X1000", sheet_count=1)
        ExcelWriter().append_record(bob_path, rec)  # Only Bob's file changes

        assert bob_fired.wait(timeout=3.0), "Bob's watcher did not fire"
        assert not alice_fired.is_set(), "Alice's watcher must not have fired"
        fw.stop()

    def test_second_instance_sees_first_instances_records(self, tmp_path):
        """Two VMs for the same user share the same file path — changes are visible."""
        wm = _wm(tmp_path, "alice")
        bt_path = wm.user_burn_table_path("alice")
        TableFactory().create(bt_path)

        vm1 = _burn_vm(bt_path, sheet_index=0)
        vm2 = _burn_vm(bt_path, sheet_index=0)

        assert len(vm1._records) == 0
        assert len(vm2._records) == 0

        # vm1 appends a record (simulates instance 1).
        rec = BurnRecord(program_number="1111-01", sheet_format="1.0037-4X2000X1000", sheet_count=1)
        ExcelWriter().append_record(bt_path, rec)

        # vm2 reloads from disk (simulates file-watcher callback on instance 2).
        vm2.load_table(bt_path)
        assert any(r.program_number == "1111-01" for r in vm2._records)
        # vm1 hasn't reloaded — it sees its own in-memory state (pre-reload).
        vm1.load_table(bt_path)
        assert any(r.program_number == "1111-01" for r in vm1._records)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Multiple files watched simultaneously
# ══════════════════════════════════════════════════════════════════════════════


class TestMultipleFilesWatched:
    def test_independent_files_fire_independent_callbacks(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        todo_path = wm.todo_path()
        MaterialRepository(path=mat_path)
        TodoRepository(path=todo_path)

        mat_fired = threading.Event()
        todo_fired = threading.Event()

        fw = _watcher()
        fw.watch(mat_path, mat_fired.set)
        fw.watch(todo_path, todo_fired.set)
        fw.start()

        time.sleep(0.02)
        mat_path.write_text(json.dumps([["A", "B"]]), encoding="utf-8")

        assert mat_fired.wait(timeout=2.0), "Materials callback did not fire"
        assert not todo_fired.is_set(), "Todo callback must not have fired"
        fw.stop()

    def test_all_three_files_watched_correctly(self, tmp_path):
        wm = _wm(tmp_path, "alice")
        mat_path = wm.materials_path()
        todo_path = wm.todo_path()
        bt_path = wm.user_burn_table_path("alice")
        MaterialRepository(path=mat_path)
        TodoRepository(path=todo_path)
        TableFactory().create(bt_path)

        mat_evt = threading.Event()
        todo_evt = threading.Event()
        bt_evt = threading.Event()

        fw = _watcher()
        fw.watch(mat_path, mat_evt.set)
        fw.watch(todo_path, todo_evt.set)
        fw.watch(bt_path, bt_evt.set)
        fw.start()

        time.sleep(0.02)
        todo_path.write_text(
            json.dumps([{"id": "x", "text": "new", "done": False}]),
            encoding="utf-8",
        )

        assert todo_evt.wait(timeout=2.0), "Todo callback did not fire"
        assert not mat_evt.is_set(), "Materials callback must not fire"
        assert not bt_evt.is_set(), "BurnTable callback must not fire"
        fw.stop()
