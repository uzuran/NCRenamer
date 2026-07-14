"""Unit tests for FileWatcher.

Calls _check_all() directly (bypassing the polling thread) so tests are
synchronous and deterministic.  A _MockRoot captures after() calls and
executes them immediately so callbacks are verifiable without a real event loop.
"""
from __future__ import annotations

import time
import threading
from pathlib import Path

import pytest

from app.utils.file_watcher import FileWatcher


# ── test helpers ──────────────────────────────────────────────────────────────


class _MockRoot:
    """Minimal stand-in for a tkinter root: records and immediately executes after() calls."""

    def __init__(self) -> None:
        self.after_calls: list[tuple[int, object]] = []

    def after(self, delay: int, callback) -> None:
        self.after_calls.append((delay, callback))
        callback()


def _fw(root=None, poll_ms: int = 500) -> FileWatcher:
    return FileWatcher(root or _MockRoot(), poll_interval_ms=poll_ms)


def _counter():
    calls: list[int] = [0]

    def cb():
        calls[0] += 1

    cb.calls = calls  # type: ignore[attr-defined]
    return cb


# ══════════════════════════════════════════════════════════════════════════════
# 1. watch() / unwatch() API
# ══════════════════════════════════════════════════════════════════════════════


class TestWatchAPI:
    def test_watch_existing_file_records_its_mtime(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("x")
        fw = _fw()
        fw.watch(f, lambda: None)
        mtime, _ = fw._watched[f]
        assert mtime == f.stat().st_mtime

    def test_watch_missing_file_records_zero_mtime(self, tmp_path):
        fw = _fw()
        fw.watch(tmp_path / "missing.json", lambda: None)
        mtime, _ = fw._watched[tmp_path / "missing.json"]
        assert mtime == 0.0

    def test_watch_replaces_previous_registration(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("x")
        fw = _fw()
        cb1, cb2 = _counter(), _counter()
        fw.watch(f, cb1)
        fw.watch(f, cb2)
        assert len(fw._watched) == 1

    def test_unwatch_removes_path(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("x")
        fw = _fw()
        fw.watch(f, lambda: None)
        fw.unwatch(f)
        assert f not in fw._watched

    def test_unwatch_missing_path_does_not_raise(self, tmp_path):
        fw = _fw()
        fw.unwatch(tmp_path / "ghost.json")  # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 2. _check_all() — change detection
# ══════════════════════════════════════════════════════════════════════════════


class TestCheckAll:
    def test_fires_callback_when_mtime_increases(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)

        # Simulate an external write by bumping mtime manually.
        new_mtime = f.stat().st_mtime + 1
        import os
        os.utime(f, (new_mtime, new_mtime))

        fw._check_all()
        assert cb.calls[0] == 1

    def test_does_not_fire_when_file_unchanged(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)
        fw._check_all()  # first check — no change yet
        fw._check_all()  # second check — still no change
        assert cb.calls[0] == 0

    def test_fires_exactly_once_per_change(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)

        import os
        new_mtime = f.stat().st_mtime + 1
        os.utime(f, (new_mtime, new_mtime))

        fw._check_all()  # fires
        fw._check_all()  # same mtime — no second fire
        assert cb.calls[0] == 1

    def test_updates_known_mtime_after_firing(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        fw.watch(f, lambda: None)

        import os
        new_mtime = f.stat().st_mtime + 1
        os.utime(f, (new_mtime, new_mtime))
        fw._check_all()

        recorded_mtime, _ = fw._watched[f]
        assert recorded_mtime == new_mtime

    def test_skips_missing_files_without_raising(self, tmp_path):
        fw = _fw()
        fw.watch(tmp_path / "ghost.json", lambda: None)
        fw._check_all()  # should not raise

    def test_detects_file_creation(self, tmp_path):
        """A file that didn't exist when registered triggers on first write."""
        f = tmp_path / "new.json"
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)  # mtime stored as 0.0

        f.write_text("created")
        fw._check_all()
        assert cb.calls[0] == 1

    def test_two_files_independent_callbacks(self, tmp_path):
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text("x")
        f2.write_text("y")
        fw = _fw()
        cb1, cb2 = _counter(), _counter()
        fw.watch(f1, cb1)
        fw.watch(f2, cb2)

        import os
        new_mtime = f1.stat().st_mtime + 1
        os.utime(f1, (new_mtime, new_mtime))

        fw._check_all()
        assert cb1.calls[0] == 1  # f1 changed
        assert cb2.calls[0] == 0  # f2 unchanged

    def test_callback_is_called_via_root_after(self, tmp_path):
        """after() must be used — not a direct callback() call."""
        f = tmp_path / "a.json"
        f.write_text("x")
        root = _MockRoot()
        fw = FileWatcher(root)
        cb = _counter()
        fw.watch(f, cb)

        import os
        new_mtime = f.stat().st_mtime + 1
        os.utime(f, (new_mtime, new_mtime))
        fw._check_all()

        assert len(root.after_calls) == 1
        delay, _ = root.after_calls[0]
        assert delay == 0

    def test_does_not_fire_for_unwatched_file(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("x")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)
        fw.unwatch(f)

        import os
        new_mtime = f.stat().st_mtime + 1
        os.utime(f, (new_mtime, new_mtime))
        fw._check_all()

        assert cb.calls[0] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 3. acknowledge_write() — self-write suppression
# ══════════════════════════════════════════════════════════════════════════════


class TestAcknowledgeWrite:
    def test_suppresses_event_after_local_write(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)

        # Simulate local write + immediate acknowledgement.
        f.write_text("v2")
        fw.acknowledge_write(f)

        fw._check_all()
        assert cb.calls[0] == 0  # no spurious callback

    def test_does_not_suppress_subsequent_external_change(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("v1")
        fw = _fw()
        cb = _counter()
        fw.watch(f, cb)

        f.write_text("v2")
        fw.acknowledge_write(f)
        fw._check_all()  # suppressed
        assert cb.calls[0] == 0

        import os
        # External write later
        new_mtime = f.stat().st_mtime + 1
        os.utime(f, (new_mtime, new_mtime))
        fw._check_all()
        assert cb.calls[0] == 1

    def test_acknowledge_on_missing_file_does_not_raise(self, tmp_path):
        fw = _fw()
        fw.watch(tmp_path / "gone.json", lambda: None)
        fw.acknowledge_write(tmp_path / "gone.json")

    def test_acknowledge_on_unwatched_path_does_not_raise(self, tmp_path):
        fw = _fw()
        fw.acknowledge_write(tmp_path / "never-watched.json")


# ══════════════════════════════════════════════════════════════════════════════
# 4. start() / stop()
# ══════════════════════════════════════════════════════════════════════════════


class TestStartStop:
    def test_start_creates_daemon_thread(self, tmp_path):
        fw = _fw()
        fw.start()
        assert fw._thread is not None
        assert fw._thread.daemon is True
        fw.stop()

    def test_start_is_idempotent(self, tmp_path):
        fw = _fw()
        fw.start()
        t1 = fw._thread
        fw.start()
        assert fw._thread is t1  # same thread, not a second one
        fw.stop()

    def test_stop_sets_running_false(self):
        fw = _fw()
        fw.start()
        fw.stop()
        assert fw._running is False

    def test_stop_without_start_does_not_raise(self):
        fw = _fw()
        fw.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 5. Real-thread integration (short poll interval, Event-based sync)
# ══════════════════════════════════════════════════════════════════════════════


class TestRealThread:
    """Lightweight integration tests with a real polling thread."""

    def test_detects_write_via_polling_thread(self, tmp_path):
        f = tmp_path / "shared.json"
        f.write_text("[]")
        fired = threading.Event()

        class _EvtRoot:
            def after(self, delay, cb):
                fired.set()
                cb()

        fw = FileWatcher(_EvtRoot(), poll_interval_ms=50)
        fw.watch(f, fired.set)
        fw.start()

        time.sleep(0.02)
        f.write_text('[{"a": 1}]')  # external write

        assert fired.wait(timeout=2.0), "Watcher did not fire within timeout"
        fw.stop()

    def test_two_files_both_detected_independently(self, tmp_path):
        f1 = tmp_path / "a.json"
        f2 = tmp_path / "b.json"
        f1.write_text("x")
        f2.write_text("y")
        evt1, evt2 = threading.Event(), threading.Event()

        class _EvtRoot:
            def after(self, delay, cb):
                cb()

        fw = FileWatcher(_EvtRoot(), poll_interval_ms=50)
        fw.watch(f1, evt1.set)
        fw.watch(f2, evt2.set)
        fw.start()

        time.sleep(0.02)
        f2.write_text("changed")

        assert evt2.wait(timeout=2.0), "f2 watcher did not fire"
        assert not evt1.is_set(), "f1 watcher must not have fired"
        fw.stop()
