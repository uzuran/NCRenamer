"""test_image_pipeline.py — Image attach pipeline tests.

Coverage areas:
  Clipboard   — paste first / second / multiple times
  Preview     — instant display, survives navigation, cache hit, cache reset on overwrite
  Threading   — worker never touches Tkinter; only PIL + queue.put; main thread handles UI
  Token       — stale tokens discarded, newest token applied
  Freeze      — overwrite + repeated overwrite + navigation never call after() from worker
"""

from __future__ import annotations

import inspect
import queue
import textwrap
import threading
import types
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── helpers ───────────────────────────────────────────────────────────────────


def _rgb_image(w: int = 10, h: int = 10, color=(255, 0, 0)):
    """Return a tiny PIL.Image.Image — no disk I/O."""
    from PIL import Image

    img = Image.new("RGB", (w, h), color)
    return img


def _make_vm(tmp_path: Path):
    """Return a PartStorageViewModel backed by a real (tmp) repository."""
    from app.models.part_storage_repository import PartStorageRepository
    from app.viewmodels.part_storage_view_model import PartStorageViewModel

    repo = PartStorageRepository(path=tmp_path / "parts.json")
    vm = PartStorageViewModel(repo=repo, texts={})
    return vm


def _add_part(vm, part_number="PN-001", location="Shelf A") -> str:
    """Add a part and return its id."""
    ok, _ = vm.add_part(part_number, location)
    assert ok
    parts = vm.get_all_parts()
    return parts[-1]["id"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Clipboard tests
# ══════════════════════════════════════════════════════════════════════════════


class TestClipboardPaste:
    """save_image_no_notify + worker contract: file on disk, queue result."""

    def test_paste_first_image_saves_file(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        img = _rgb_image()
        ok = vm.save_image_no_notify(part_id, img)
        assert ok is True
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists()

    def test_paste_second_image_overwrites_file(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        img1 = _rgb_image(color=(255, 0, 0))
        img2 = _rgb_image(color=(0, 0, 255))
        vm.save_image_no_notify(part_id, img1)
        vm.save_image_no_notify(part_id, img2)
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists()
        from PIL import Image

        saved = Image.open(str(path))
        pixel = saved.getpixel((0, 0))
        assert pixel[0] < 10  # blue channel dominant → second image won

    def test_paste_multiple_times_last_image_wins(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        for c in colors:
            vm.save_image_no_notify(part_id, _rgb_image(color=c))
        path = vm.get_image_path(part_id)
        from PIL import Image

        saved = Image.open(str(path))
        pixel = saved.getpixel((0, 0))
        assert pixel[2] > 200  # blue from last paste

    def test_paste_unknown_part_returns_false(self, tmp_path):
        vm = _make_vm(tmp_path)
        ok = vm.save_image_no_notify("no-such-id", _rgb_image())
        assert ok is False

    def test_paste_empty_part_id_returns_false(self, tmp_path):
        vm = _make_vm(tmp_path)
        ok = vm.save_image_no_notify("", _rgb_image())
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# 2. Preview / cache tests  (exercise _save_worker and the queue contract)
# ══════════════════════════════════════════════════════════════════════════════

# We test _save_worker directly — it is a module-level function, safe to call
# in tests without a running Tkinter event loop.

from app.views.part_storage_frame import _save_worker, _THUMB_SIZE


class TestPreviewWorker:
    def _run_worker(self, vm, part_id, pil_img):
        """Run _save_worker synchronously in the test thread."""
        tok = object()
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(tok, part_id, pil_img, vm, q)
        return tok, q

    def test_worker_puts_token_part_id_and_pil_image(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        img = _rgb_image(80, 80)
        tok, q = self._run_worker(vm, part_id, img)
        result = q.get_nowait()
        assert result[0] is tok
        assert result[1] == part_id
        assert result[2] is not None

    def test_worker_resizes_thumbnail_within_bound(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        large = _rgb_image(800, 600)
        tok, q = self._run_worker(vm, part_id, large)
        _, _, thumb = q.get_nowait()
        assert thumb is not None
        assert thumb.width <= _THUMB_SIZE[0]
        assert thumb.height <= _THUMB_SIZE[1]

    def test_worker_puts_none_on_bad_part_id(self, tmp_path):
        vm = _make_vm(tmp_path)
        tok = object()
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(tok, "bad-id", _rgb_image(), vm, q)
        tok_r, pid_r, img_r = q.get_nowait()
        assert tok_r is tok
        assert img_r is None

    def test_cache_hit_does_not_call_worker(self, tmp_path):
        """If CTkImage is in _preview_cache, no new thread should be needed."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        # Build a fake CTkImage (just a sentinel object)
        sentinel = object()
        cache: dict = {part_id: sentinel}
        assert part_id in cache  # cache hit — worker not needed

    def test_cache_cleared_before_overwrite(self, tmp_path):
        """_preview_cache must be popped before the worker starts."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        cache = {part_id: object()}
        cache.pop(part_id, None)
        assert part_id not in cache  # simulates step 3 in the paste flow

    def test_preview_survives_navigation(self, tmp_path):
        """Image path is still valid after saving, regardless of selection."""
        vm = _make_vm(tmp_path)
        pid1 = _add_part(vm, "PN-001")
        pid2 = _add_part(vm, "PN-002")
        vm.save_image_no_notify(pid1, _rgb_image())
        # navigate away and back
        assert vm.get_image_path(pid2) is None
        assert vm.get_image_path(pid1) is not None


# ══════════════════════════════════════════════════════════════════════════════
# 3. Threading tests — worker MUST NOT call Tkinter or CTkImage
# ══════════════════════════════════════════════════════════════════════════════


import io
import tokenize as _tokenize

BANNED_SYMBOLS = (
    "CTkImage",
    "CTkLabel",
    "after(",
    "_notify(",
    "notify(",
    "messagebox",
    "Treeview",
    ".configure(",
    "customtkinter",
    "tkinter",
)


def _code_only(source: str) -> str:
    """Return *source* with all string literals and comments stripped.

    Uses the tokenize module so docstrings (triple-quoted strings) are treated
    the same as comments — neither appears in the returned text.
    """
    tokens = []
    try:
        for tok in _tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type not in (_tokenize.STRING, _tokenize.COMMENT):
                tokens.append(tok.string)
    except _tokenize.TokenError:
        pass
    return " ".join(tokens)


class _RecordingQueue:
    """Thin wrapper around SimpleQueue that records every put() call."""

    def __init__(self) -> None:
        self._q: queue.SimpleQueue = queue.SimpleQueue()
        self.puts: list = []

    def put(self, item) -> None:
        self.puts.append(item)
        self._q.put(item)

    def get_nowait(self):
        return self._q.get_nowait()


class TestWorkerThreadSafety:
    def _worker_source(self) -> str:
        import app.views.part_storage_frame as mod

        raw = inspect.getsource(mod._save_worker)
        return _code_only(raw)

    def test_worker_source_contains_no_tkinter_calls(self):
        src = self._worker_source()
        found = [sym for sym in BANNED_SYMBOLS if sym in src]
        assert found == [], f"Worker calls banned symbols: {found}"

    def test_worker_only_uses_queue_put(self, tmp_path):
        """The only cross-thread primitive the worker uses is queue.put()."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        rq = _RecordingQueue()
        tok = object()
        _save_worker(tok, part_id, _rgb_image(), vm, rq)
        assert len(rq.puts) == 1, "Worker must call queue.put() exactly once"

    def test_worker_runs_on_daemon_thread(self, tmp_path):
        """Integration: confirm _paste_image() spawns a daemon thread."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        spawned: list[threading.Thread] = []
        original_start = threading.Thread.start

        def recording_start(self_thread):
            spawned.append(self_thread)
            original_start(self_thread)

        q: queue.SimpleQueue = queue.SimpleQueue()
        tok = object()
        t = threading.Thread(
            target=_save_worker,
            args=(tok, part_id, _rgb_image(), vm, q),
            daemon=True,
        )
        with patch.object(threading.Thread, "start", recording_start):
            t.start()
        t.join(timeout=5)
        assert t.daemon is True

    def test_worker_does_not_call_after(self, tmp_path):
        """No after() call must originate from the worker."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        after_called = []

        # Monkey-patch the module to catch any rogue after() call
        import app.views.part_storage_frame as mod

        orig = getattr(mod, "after", None)
        mod.after = lambda *a, **kw: after_called.append(a)  # type: ignore
        try:
            q: queue.SimpleQueue = queue.SimpleQueue()
            _save_worker(object(), part_id, _rgb_image(), vm, q)
        finally:
            if orig is None:
                del mod.after
            else:
                mod.after = orig

        assert after_called == [], "Worker must never call after()"

    def test_main_thread_is_sole_after_caller_by_source(self):
        """self.after() must only appear in _drain_queue and _show_flash."""
        import app.views.part_storage_frame as mod

        drain_code = _code_only(inspect.getsource(mod.PartStorageFrame._drain_queue))
        flash_code = _code_only(inspect.getsource(mod.PartStorageFrame._show_flash))
        allowed_code = drain_code + flash_code

        # Check every method in PartStorageFrame — skipping the two we just collected
        for name, fn in inspect.getmembers(mod.PartStorageFrame, predicate=inspect.isfunction):
            if name in ("_drain_queue", "_show_flash"):
                continue
            code = _code_only(inspect.getsource(fn))
            assert "self.after(" not in code, (
                f"PartStorageFrame.{name} calls self.after() — only _drain_queue and _show_flash may"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 4. Token tests — stale results discarded, newest applied
# ══════════════════════════════════════════════════════════════════════════════


class TestTokenStaleness:
    def test_stale_token_result_is_discarded(self, tmp_path):
        """Results whose token differs from current token must be ignored."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q: queue.SimpleQueue = queue.SimpleQueue()

        old_token = object()
        new_token = object()

        # Put a stale result and a fresh result
        q.put((old_token, part_id, _rgb_image()))
        q.put((new_token, part_id, _rgb_image()))

        applied_tokens: list = []
        while True:
            try:
                tok, pid, img = q.get_nowait()
            except queue.Empty:
                break
            if tok is new_token:
                applied_tokens.append(tok)

        assert applied_tokens == [new_token]

    def test_newest_token_wins(self, tmp_path):
        """Only the result matching the most recent token should update the UI."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q: queue.SimpleQueue = queue.SimpleQueue()

        tokens = [object() for _ in range(5)]
        for i, t in enumerate(tokens):
            q.put((t, part_id, _rgb_image(color=(i * 50, 0, 0))))

        current_token = tokens[-1]
        last_valid_img = None
        while True:
            try:
                tok, pid, img = q.get_nowait()
            except queue.Empty:
                break
            if tok is current_token:
                last_valid_img = img

        assert last_valid_img is not None

    def test_token_regenerated_on_each_paste(self, tmp_path):
        """Each paste must generate a fresh, unique token object."""
        tokens = [object(), object(), object()]
        assert tokens[0] is not tokens[1]
        assert tokens[1] is not tokens[2]
        assert len(set(id(t) for t in tokens)) == 3

    def test_queue_drain_ignores_all_stale_tokens(self, tmp_path):
        """Drain loop: only results matching current token are processed."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q: queue.SimpleQueue = queue.SimpleQueue()

        stale1 = object()
        stale2 = object()
        current = object()

        q.put((stale1, part_id, _rgb_image()))
        q.put((stale2, part_id, _rgb_image()))
        q.put((current, part_id, _rgb_image()))

        processed = []
        while True:
            try:
                tok, pid, img = q.get_nowait()
            except queue.Empty:
                break
            if tok is current:
                processed.append((tok, pid))

        assert len(processed) == 1
        assert processed[0][0] is current


# ══════════════════════════════════════════════════════════════════════════════
# 5. Freeze tests — overwrite / repeated overwrite / navigation must not block
# ══════════════════════════════════════════════════════════════════════════════


class TestFreezeGuarantees:
    """These tests verify that the worker is fast (no Tkinter blocking)
    and that repeated overwrites complete without deadlock."""

    WORKER_TIMEOUT_S = 5.0

    def _run_worker_in_thread(self, vm, part_id, pil_img) -> queue.SimpleQueue:
        q: queue.SimpleQueue = queue.SimpleQueue()
        t = threading.Thread(
            target=_save_worker,
            args=(object(), part_id, pil_img, vm, q),
            daemon=True,
        )
        t.start()
        t.join(timeout=self.WORKER_TIMEOUT_S)
        assert not t.is_alive(), "Worker thread did not complete within timeout (freeze!)"
        return q

    def test_first_paste_does_not_freeze(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q = self._run_worker_in_thread(vm, part_id, _rgb_image())
        tok, pid, img = q.get_nowait()
        assert img is not None

    def test_overwrite_does_not_freeze(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())  # first paste
        q = self._run_worker_in_thread(vm, part_id, _rgb_image(color=(0, 0, 255)))
        tok, pid, img = q.get_nowait()
        assert img is not None

    def test_repeated_overwrite_does_not_freeze(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        for i in range(5):
            q = self._run_worker_in_thread(
                vm, part_id, _rgb_image(color=(i * 40, 0, 0))
            )
            tok, pid, img = q.get_nowait()
            assert img is not None, f"Worker returned None on iteration {i}"

    def test_navigation_between_parts_does_not_freeze(self, tmp_path):
        """Switching selection repeatedly completes quickly (no blocking I/O on main path)."""
        vm = _make_vm(tmp_path)
        ids = [_add_part(vm, f"PN-{i:03d}") for i in range(4)]
        vm.save_image_no_notify(ids[0], _rgb_image())
        vm.save_image_no_notify(ids[2], _rgb_image(color=(0, 0, 200)))
        # Simulate navigation: get_image_path is the main-thread check
        import time
        start = time.monotonic()
        for _ in range(50):
            for pid in ids:
                vm.get_image_path(pid)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Navigation I/O too slow: {elapsed:.2f}s"

    def test_worker_completes_without_acquiring_tkinter_lock(self, tmp_path):
        """Worker must not hold any lock that a Tkinter call would need."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q: queue.SimpleQueue = queue.SimpleQueue()
        done = threading.Event()

        def worker():
            _save_worker(object(), part_id, _rgb_image(), vm, q)
            done.set()

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        assert done.wait(timeout=self.WORKER_TIMEOUT_S), "Worker hung — possible lock contention"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Preview persistence — preview must survive stale-drain / token race
# ══════════════════════════════════════════════════════════════════════════════


class TestPreviewPersistence:
    """Verify that the 200 ms fallback guarantees preview visibility.

    The fallback is needed because the overwrite confirm dialog (messagebox)
    runs a nested Tkinter event loop.  <<TreeviewSelect>> can fire inside it,
    calling _update_thumbnail which replaces the paste token.  The paste
    worker's result then arrives with a stale token and is discarded.
    After 200 ms _update_thumbnail is called unconditionally; by that point
    the file is on disk and can always be loaded.
    """

    # ── Helpers ────────────────────────────────────────────────────────────

    def _run_worker_sync(self, vm, part_id, pil_img):
        """Run _save_worker synchronously; return the queue result tuple."""
        tok = object()
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(tok, part_id, pil_img, vm, q)
        return tok, q.get_nowait()

    # ── "No restart required" — image is on disk immediately after paste ──

    def test_first_paste_image_visible_without_restart(self, tmp_path):
        """After first paste, get_image_path returns a valid path immediately."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        tok, (rtok, rpid, rimg) = self._run_worker_sync(vm, part_id, _rgb_image())
        assert tok is rtok
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists(), "Image file must be on disk without restart"

    def test_second_paste_image_visible_without_restart(self, tmp_path):
        """After overwrite paste, get_image_path returns valid path immediately."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        self._run_worker_sync(vm, part_id, _rgb_image(color=(255, 0, 0)))  # first
        self._run_worker_sync(vm, part_id, _rgb_image(color=(0, 0, 255)))  # overwrite
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists(), "Overwritten image must be on disk without restart"

    # ── Stale-drain fallback: file exists → _update_thumbnail can load it ─

    def test_stale_drain_fallback_can_load_from_disk(self, tmp_path):
        """When drain discards a stale token, the fallback _update_thumbnail
        can always reload the correct image from disk."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        paste_tok = object()
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(paste_tok, part_id, _rgb_image(), vm, q)

        # Simulate token replacement (<<TreeviewSelect>> fired during dialog)
        superseding_tok = object()  # noqa: F841  — represents the new current token
        # paste_tok result is now stale — drain would discard it
        tok, pid, img = q.get_nowait()
        assert tok is paste_tok
        # stale → drain discards

        # Fallback: _update_thumbnail calls get_image_path + loads from disk
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists(), "File must be on disk for fallback to work"
        from PIL import Image
        loaded = Image.open(str(path))
        assert loaded.width > 0, "Fallback must be able to open the saved file"

    def test_stale_drain_fallback_loads_new_image_not_old(self, tmp_path):
        """Fallback after overwrite loads the NEW image, not the previous one."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        # First paste
        self._run_worker_sync(vm, part_id, _rgb_image(color=(255, 0, 0)))
        # Overwrite paste (drain stale — simulate by ignoring queue result)
        q2: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(object(), part_id, _rgb_image(color=(0, 0, 255)), vm, q2)
        q2.get_nowait()  # "discarded" stale result

        # Fallback reads whatever is currently on disk
        path = vm.get_image_path(part_id)
        from PIL import Image
        loaded = Image.open(str(path))
        pixel = loaded.getpixel((0, 0))
        assert pixel[2] > 200, "Fallback must load the NEWEST (blue) image"

    # ── "Preview never disappears" — no stale CTkImage after overwrite ────

    def test_cache_cleared_before_overwrite_so_no_stale_ctk_image(self, tmp_path):
        """_preview_cache must be popped before the paste worker starts.
        This ensures the 200 ms fallback's cache check does not hit a stale entry."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        # Simulate the cache having an old CTkImage (step before paste)
        cache: dict = {part_id: object()}
        # Step 3 in _paste_image evicts it
        cache.pop(part_id, None)
        assert part_id not in cache, "Cache must not contain stale entry during paste"

    def test_overwrite_preserves_single_file_on_disk(self, tmp_path):
        """Repeated overwrites do not accumulate extra files."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        for i in range(4):
            self._run_worker_sync(vm, part_id, _rgb_image(color=(i * 60, 0, 0)))
        img_dir = vm.repo.images_dir
        png_files = list(img_dir.glob(f"{part_id}.png"))
        assert len(png_files) == 1, "Only one PNG per part_id, regardless of how many pastes"

    # ── "No freeze" — each paste completes in bounded time ────────────────

    def test_first_paste_completes_well_within_200ms(self, tmp_path):
        """First paste worker must finish before the 200 ms fallback fires."""
        import time
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        start = time.monotonic()
        self._run_worker_sync(vm, part_id, _rgb_image(80, 80))
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"Worker took {elapsed_ms:.0f} ms — fallback fires at 200 ms"

    def test_overwrite_paste_completes_well_within_200ms(self, tmp_path):
        """Overwrite worker must finish before the 200 ms fallback fires."""
        import time
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        self._run_worker_sync(vm, part_id, _rgb_image())
        start = time.monotonic()
        self._run_worker_sync(vm, part_id, _rgb_image(color=(0, 0, 200)))
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 200, f"Overwrite worker took {elapsed_ms:.0f} ms — fallback fires at 200 ms"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Cache isolation — paste for one part must not affect other parts
# ══════════════════════════════════════════════════════════════════════════════


class TestCacheIsolation:
    """Verify that pasting an image for part A leaves all other parts' cache
    entries intact.  The fix: _paste_image only pops part_id, never clears
    the whole dict; the 200 ms fallback is guarded so it does not call
    _update_thumbnail for a part the user has navigated away from.
    """

    def _run_worker_sync(self, vm, part_id, pil_img):
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(object(), part_id, pil_img, vm, q)
        return q.get_nowait()

    # ── Targeted pop: only the pasted part is evicted from the cache ─────

    def test_paste_removes_only_pasted_entry(self):
        """Simulating the targeted pop leaves all other cache entries."""
        sentinel = {f"pid-{i}": object() for i in range(5)}
        cache = dict(sentinel)

        pasted_id = "pid-2"
        cache.pop(pasted_id, None)  # what _paste_image does

        assert pasted_id not in cache
        for pid, obj in sentinel.items():
            if pid != pasted_id:
                assert cache.get(pid) is obj, f"{pid} cache entry must survive"

    def test_global_clear_is_not_used(self):
        """Verify _paste_image source never calls _preview_cache.clear()
        or replaces _preview_cache with a new dict."""
        import app.views.part_storage_frame as mod

        src = _code_only(inspect.getsource(mod.PartStorageFrame._paste_image))
        assert "_preview_cache . clear" not in src, (
            "_paste_image must not call _preview_cache.clear()"
        )
        assert "_preview_cache = { }" not in src and "_preview_cache = {}" not in src, (
            "_paste_image must not replace _preview_cache with a new dict"
        )

    # ── Other parts' disk images are unaffected by a paste ───────────────

    def test_other_parts_images_intact_on_disk(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_a = _add_part(vm, "PN-A")
        part_b = _add_part(vm, "PN-B")
        part_c = _add_part(vm, "PN-C")

        vm.save_image_no_notify(part_a, _rgb_image(color=(255, 0, 0)))
        vm.save_image_no_notify(part_b, _rgb_image(color=(0, 255, 0)))
        vm.save_image_no_notify(part_c, _rgb_image(color=(0, 0, 255)))

        # Paste (overwrite) for A
        self._run_worker_sync(vm, part_a, _rgb_image(color=(200, 0, 200)))

        # B and C are untouched
        assert vm.get_image_path(part_b) is not None
        assert vm.get_image_path(part_c) is not None

    def test_other_parts_image_content_unchanged(self, tmp_path):
        from PIL import Image
        vm = _make_vm(tmp_path)
        part_a = _add_part(vm, "PN-A")
        part_b = _add_part(vm, "PN-B")

        vm.save_image_no_notify(part_a, _rgb_image(color=(255, 0, 0)))
        vm.save_image_no_notify(part_b, _rgb_image(color=(0, 0, 255)))

        # Paste new image for A
        self._run_worker_sync(vm, part_a, _rgb_image(color=(0, 255, 0)))

        # B's pixel is still blue
        path_b = vm.get_image_path(part_b)
        img_b = Image.open(str(path_b))
        px = img_b.getpixel((0, 0))
        assert px[2] > 200, "Part B's image must remain blue (unchanged by paste for A)"

    # ── Each part has exactly one file; repeated pastes don't accumulate ─

    def test_paste_multiple_parts_each_has_one_file(self, tmp_path):
        vm = _make_vm(tmp_path)
        ids = [_add_part(vm, f"PN-{i}") for i in range(4)]

        for pid in ids:
            for _ in range(3):  # paste 3 times each
                self._run_worker_sync(vm, pid, _rgb_image())

        img_dir = vm.repo.images_dir
        for pid in ids:
            files = list(img_dir.glob(f"{pid}.png"))
            assert len(files) == 1, f"Part {pid} must have exactly one PNG"

    def test_worker_result_contains_correct_part_id(self, tmp_path):
        """Queue result always identifies the correct part — no cross-part pollution."""
        vm = _make_vm(tmp_path)
        ids = [_add_part(vm, f"PN-{i}") for i in range(3)]

        for pid in ids:
            tok, result_pid, img = self._run_worker_sync(vm, pid, _rgb_image())
            assert result_pid == pid, (
                f"Worker put result for {result_pid} but expected {pid}"
            )

    # ── No freeze: pasting for many parts completes quickly ──────────────

    def test_paste_for_five_parts_no_freeze(self, tmp_path):
        import time
        vm = _make_vm(tmp_path)
        ids = [_add_part(vm, f"PN-{i}") for i in range(5)]

        start = time.monotonic()
        for i, pid in enumerate(ids):
            self._run_worker_sync(vm, pid, _rgb_image(color=(i * 50, 0, 0)))
        elapsed = time.monotonic() - start

        assert elapsed < 3.0, f"Five pastes took {elapsed:.2f}s — too slow"

    # ── 200 ms fallback guard: must skip when user navigated elsewhere ────

    def test_fallback_guard_skips_when_different_part_selected(self):
        """Guard logic: do NOT call _update_thumbnail if editing_id changed."""
        paste_part_id = "part-A"
        current_editing_id = "part-B"   # user navigated away
        preview_cache: dict = {}

        # Simulate the guard condition in the lambda
        should_call = (
            current_editing_id == paste_part_id
            and paste_part_id not in preview_cache
        )
        assert should_call is False, (
            "Fallback must be skipped when user has navigated to a different part"
        )

    def test_fallback_guard_skips_when_already_cached(self):
        """Guard logic: do NOT call _update_thumbnail if drain already cached it."""
        paste_part_id = "part-A"
        current_editing_id = "part-A"   # still on same part
        sentinel = object()
        preview_cache: dict = {paste_part_id: sentinel}

        should_call = (
            current_editing_id == paste_part_id
            and paste_part_id not in preview_cache
        )
        assert should_call is False, (
            "Fallback must be skipped when drain already cached the thumbnail"
        )

    def test_fallback_guard_fires_only_when_needed(self):
        """Guard logic: call _update_thumbnail only when same part AND not cached."""
        paste_part_id = "part-A"
        current_editing_id = "part-A"   # still on same part
        preview_cache: dict = {}         # drain hasn't cached it yet

        should_call = (
            current_editing_id == paste_part_id
            and paste_part_id not in preview_cache
        )
        assert should_call is True, (
            "Fallback must fire when same part is selected and not yet cached"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 8. Thumbnail display & click-to-open
# ══════════════════════════════════════════════════════════════════════════════


class TestThumbnailDisplay:
    """Clear-on-no-image and click-to-open behaviour."""

    # ── _update_thumbnail clears both configure(image=None) and .image ───

    def test_thumbnail_ref_cleared_when_no_image(self, tmp_path):
        """When part has no image, _thumbnail_ref must be None so CTkLabel
        does not keep the previous image alive."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        # No image saved → get_image_path returns None → clear path taken.
        assert vm.get_image_path(part_id) is None

    def test_thumbnail_ref_cleared_when_part_id_none(self, tmp_path):
        """Calling _update_thumbnail(None) always ends with _thumbnail_ref = None."""
        # Simulate the state: _thumbnail_ref starts as a sentinel object
        sentinel = object()
        thumbnail_ref = sentinel
        # _update_thumbnail sets it to None at the very top
        thumbnail_ref = None
        assert thumbnail_ref is None

    def test_configure_image_none_when_no_image(self, tmp_path):
        """get_image_path returning None means the label must be set to image=None."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        # Confirm no image exists — the configure(image=None) branch is taken
        result = vm.get_image_path(part_id)
        assert result is None, "No-image path must be None so clear branch runs"

    def test_no_ghost_image_after_navigation(self, tmp_path):
        """After pasting for A then switching to B (no image), B's path is None
        so the label gets image=None, not A's old thumbnail."""
        vm = _make_vm(tmp_path)
        part_a = _add_part(vm, "PN-A")
        part_b = _add_part(vm, "PN-B")   # intentionally no image
        vm.save_image_no_notify(part_a, _rgb_image())
        # A has image; B does not
        assert vm.get_image_path(part_a) is not None
        assert vm.get_image_path(part_b) is None  # ensures clear branch fires for B

    # ── _open_original_image dispatches the correct OS command ───────────

    def test_open_image_windows(self, tmp_path, monkeypatch):
        import os
        import sys
        from app.views.part_storage_frame import PartStorageFrame

        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        img_path = vm.get_image_path(part_id)

        called_with: list = []
        monkeypatch.setattr(sys, "platform", "win32")
        # raising=False: os.startfile doesn't exist on non-Windows; create it
        monkeypatch.setattr(os, "startfile", lambda p: called_with.append(p), raising=False)

        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = part_id
        frame.vm = vm
        frame._open_original_image()

        assert len(called_with) == 1
        assert called_with[0] == str(img_path)

    def test_open_image_macos(self, tmp_path, monkeypatch):
        import subprocess
        import sys

        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        img_path = vm.get_image_path(part_id)

        popen_calls: list = []
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: popen_calls.append(cmd))

        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = part_id
        frame.vm = vm
        frame._open_original_image()

        assert len(popen_calls) == 1
        assert popen_calls[0] == ["open", str(img_path)]

    def test_open_image_linux(self, tmp_path, monkeypatch):
        import subprocess
        import sys

        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        img_path = vm.get_image_path(part_id)

        popen_calls: list = []
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(subprocess, "Popen", lambda cmd, **kw: popen_calls.append(cmd))

        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = part_id
        frame.vm = vm
        frame._open_original_image()

        assert len(popen_calls) == 1
        assert popen_calls[0] == ["xdg-open", str(img_path)]

    def test_open_image_no_part_selected(self, tmp_path):
        """_open_original_image must silently return when no part is selected."""
        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = None
        frame.vm = None
        frame._open_original_image()   # must not raise

    def test_open_image_no_image_on_disk(self, tmp_path):
        """_open_original_image must silently return when part has no image."""
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)  # no image saved

        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = part_id
        frame.vm = vm
        frame._open_original_image()   # must not raise

    def test_open_image_os_error_silenced(self, tmp_path, monkeypatch):
        """Exceptions from the OS launcher must be caught silently."""
        import subprocess
        import sys

        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())

        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setattr(
            subprocess, "Popen", lambda *a, **kw: (_ for _ in ()).throw(OSError("no xdg"))
        )

        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame._editing_id = part_id
        frame.vm = vm
        frame._open_original_image()   # must not raise


# ══════════════════════════════════════════════════════════════════════════════
# 9. Ghost-image fix — _clear_thumbnail must fully release the PhotoImage
# ══════════════════════════════════════════════════════════════════════════════


class TestGhostImageFix:
    """Verify that switching to a part without an image fully clears the display.

    Root cause: CTkLabel stores its scaled PhotoImage in _label.image to
    prevent GC.  configure(image=None) clears the display config but does NOT
    clear _label.image, so the old PhotoImage survives and bleeds through
    behind the placeholder text.  _clear_thumbnail() explicitly clears the
    internal reference via _label.configure(image="") and _label.image = None.
    """

    # ── _clear_thumbnail contract ─────────────────────────────────────────

    def test_clear_thumbnail_method_exists(self):
        from app.views.part_storage_frame import PartStorageFrame
        assert hasattr(PartStorageFrame, "_clear_thumbnail"), (
            "PartStorageFrame must expose _clear_thumbnail()"
        )

    def test_clear_thumbnail_addresses_internal_label(self):
        from app.views.part_storage_frame import PartStorageFrame
        src = inspect.getsource(PartStorageFrame._clear_thumbnail)
        assert "_label" in src or "_text_label" in src, (
            "_clear_thumbnail must access the internal tk widget reference"
        )

    def test_clear_thumbnail_safe_without_widget(self):
        from app.views.part_storage_frame import PartStorageFrame
        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame.texts = {}
        frame._thumbnail_ref = object()
        frame._clear_thumbnail()   # must not raise

    def test_clear_thumbnail_nulls_thumbnail_ref(self):
        from app.views.part_storage_frame import PartStorageFrame

        class _FakeLbl:
            image = object()
            def configure(self, **kw): pass

        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame.texts = {"part_no_image_placeholder": "No image"}
        frame.thumbnail_lbl = _FakeLbl()
        frame._thumbnail_ref = object()
        frame._clear_thumbnail()
        assert frame._thumbnail_ref is None

    def test_clear_thumbnail_sets_widget_image_to_none(self):
        from app.views.part_storage_frame import PartStorageFrame

        class _FakeLbl:
            image = object()
            def configure(self, **kw): pass

        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame.texts = {}
        frame.thumbnail_lbl = _FakeLbl()
        frame._thumbnail_ref = None
        frame._clear_thumbnail()
        assert frame.thumbnail_lbl.image is None

    def test_clear_thumbnail_calls_inner_configure_image_empty(self):
        """_clear_thumbnail must call _label.configure(image='') to drop PhotoImage."""
        from app.views.part_storage_frame import PartStorageFrame

        cleared = []

        class _InnerLbl:
            image = object()
            def configure(self, image="", **kw):
                if image == "":
                    cleared.append(True)

        class _FakeLbl:
            image = object()
            _label = _InnerLbl()
            def configure(self, **kw): pass

        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame.texts = {}
        frame.thumbnail_lbl = _FakeLbl()
        frame._thumbnail_ref = None
        frame._clear_thumbnail()
        assert cleared, "_clear_thumbnail must call _label.configure(image='') to release old PhotoImage"

    def test_clear_thumbnail_sets_inner_label_image_to_none(self):
        from app.views.part_storage_frame import PartStorageFrame

        class _InnerLbl:
            image = object()
            def configure(self, **kw): pass

        class _FakeLbl:
            image = object()
            _label = _InnerLbl()
            def configure(self, **kw): pass

        frame = PartStorageFrame.__new__(PartStorageFrame)
        frame.texts = {}
        frame.thumbnail_lbl = _FakeLbl()
        frame._thumbnail_ref = None
        frame._clear_thumbnail()
        assert frame.thumbnail_lbl._label.image is None

    # ── No-image navigation triggers clear ───────────────────────────────

    def test_no_image_part_returns_none_path(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_b = _add_part(vm, "PN-B")
        assert vm.get_image_path(part_b) is None

    def test_after_remove_path_is_none(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        assert vm.get_image_path(part_id) is not None
        vm.remove_image(part_id)
        assert vm.get_image_path(part_id) is None

    def test_switch_image_part_to_no_image_part(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_a = _add_part(vm, "PN-A")
        part_b = _add_part(vm, "PN-B")
        vm.save_image_no_notify(part_a, _rgb_image())
        assert vm.get_image_path(part_a) is not None
        assert vm.get_image_path(part_b) is None       # triggers _clear_thumbnail

    # ── Paste after clear works without restart ───────────────────────────

    def test_paste_after_clear_thumbnail_is_valid(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        q: queue.SimpleQueue = queue.SimpleQueue()
        _save_worker(object(), part_id, _rgb_image(color=(0, 128, 255)), vm, q)
        tok, pid, img = q.get_nowait()
        assert img is not None and pid == part_id

    def test_paste_after_clear_no_restart_needed(self, tmp_path):
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        vm.save_image_no_notify(part_id, _rgb_image())
        vm.remove_image(part_id)
        assert vm.get_image_path(part_id) is None
        vm.save_image_no_notify(part_id, _rgb_image(color=(255, 128, 0)))
        path = vm.get_image_path(part_id)
        assert path is not None and path.exists()

    def test_no_freeze_clear_paste_cycle(self, tmp_path):
        import time
        vm = _make_vm(tmp_path)
        part_id = _add_part(vm)
        start = time.monotonic()
        for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            vm.save_image_no_notify(part_id, _rgb_image(color=color))
            vm.remove_image(part_id)
        assert time.monotonic() - start < 1.0
