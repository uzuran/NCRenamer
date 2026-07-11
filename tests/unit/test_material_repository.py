# tests/unit/test_material_repository.py
"""Unit tests for MaterialRepository — CRUD, atomicity, locking, path, migration."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import pytest

from app.models.material_repository import MaterialRepository
from app.utils.shared_storage import exe_dir


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_json(tmp_path: Path, rows: list[list[str]] | None = None) -> Path:
    """Write a JSON material file and return its path (always creates the file)."""
    p = tmp_path / "materials.json"
    p.write_text(json.dumps(rows if rows is not None else [], ensure_ascii=False), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def repo(tmp_path) -> MaterialRepository:
    """Fresh repository backed by an empty temp JSON file."""
    return MaterialRepository(path=_make_json(tmp_path))


@pytest.fixture
def repo_with_data(tmp_path) -> MaterialRepository:
    """Repository pre-loaded with two entries."""
    p = _make_json(tmp_path, [["1.4301BRUS-4.0", "1.4301 brus"], ["1.0037-2.0", "1.0037"]])
    return MaterialRepository(path=p)


# --------------------------------------------------------------------------- #
# load_materials
# --------------------------------------------------------------------------- #


def test_load_materials_empty_file(repo):
    assert repo.load_materials() == []


def test_load_materials_returns_all_entries(repo_with_data):
    result = repo_with_data.load_materials()
    assert len(result) == 2


def test_load_materials_returns_correct_values(repo_with_data):
    result = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert result["1.4301BRUS-4.0"] == "1.4301 brus"
    assert result["1.0037-2.0"] == "1.0037"


def test_load_materials_missing_file_returns_empty(tmp_path):
    p = tmp_path / "materials.json"
    repo = MaterialRepository(path=p)
    p.unlink()
    assert repo.load_materials() == []


def test_load_materials_skips_short_rows(tmp_path):
    p = tmp_path / "materials.json"
    p.write_text(json.dumps([["only_one"], ["A", "B"]]), encoding="utf-8")
    repo = MaterialRepository(path=p)
    assert repo.load_materials() == [["A", "B"]]


# --------------------------------------------------------------------------- #
# add_material
# --------------------------------------------------------------------------- #


def test_add_material_returns_true(repo):
    assert repo.add_material("1.4301BRUS-4.0", "1.4301 brus") is True


def test_add_material_persists(repo):
    repo.add_material("1.4301BRUS-4.0", "1.4301 brus")
    assert repo.load_materials() == [["1.4301BRUS-4.0", "1.4301 brus"]]


def test_add_material_strips_whitespace(repo):
    repo.add_material("  1.4301  ", "  1.4301 brus  ")
    loaded = repo.load_materials()
    assert loaded[0] == ["1.4301", "1.4301 brus"]


def test_add_material_rejects_duplicate(repo):
    repo.add_material("X", "x")
    assert repo.add_material("X", "y") is False


def test_add_material_duplicate_leaves_original_unchanged(repo):
    repo.add_material("X", "x")
    repo.add_material("X", "different")
    assert repo.load_materials() == [["X", "x"]]


def test_add_multiple_materials(repo):
    repo.add_material("A", "a")
    repo.add_material("B", "b")
    assert len(repo.load_materials()) == 2


# --------------------------------------------------------------------------- #
# delete_material
# --------------------------------------------------------------------------- #


def test_delete_material_returns_true(repo_with_data):
    assert repo_with_data.delete_material("1.4301BRUS-4.0") is True


def test_delete_material_removes_entry(repo_with_data):
    repo_with_data.delete_material("1.4301BRUS-4.0")
    keys = [r[0] for r in repo_with_data.load_materials()]
    assert "1.4301BRUS-4.0" not in keys


def test_delete_material_preserves_others(repo_with_data):
    repo_with_data.delete_material("1.4301BRUS-4.0")
    assert repo_with_data.load_materials() == [["1.0037-2.0", "1.0037"]]


def test_delete_material_missing_returns_false(repo_with_data):
    assert repo_with_data.delete_material("NONEXISTENT") is False


def test_delete_material_strips_whitespace(repo_with_data):
    assert repo_with_data.delete_material("  1.4301BRUS-4.0  ") is True


# --------------------------------------------------------------------------- #
# update_material
# --------------------------------------------------------------------------- #


def test_update_material_returns_true(repo_with_data):
    assert repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "new") is True


def test_update_material_changes_value(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 new"


def test_update_material_renames_incorrect_key(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-NEW", "new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert "1.4301BRUS-NEW" in rows
    assert "1.4301BRUS-4.0" not in rows


def test_update_material_preserves_other_entries(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.0037-2.0"] == "1.0037"


def test_update_material_missing_returns_false(repo_with_data):
    assert repo_with_data.update_material("NONEXISTENT", "NONEXISTENT", "x") is False


def test_update_material_strips_whitespace(repo_with_data):
    repo_with_data.update_material("  1.4301BRUS-4.0  ", "1.4301BRUS-4.0", "  new  ")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.4301BRUS-4.0"] == "new"


def test_update_material_persists_across_instances(tmp_path):
    p = _make_json(tmp_path, [["X", "x"]])
    MaterialRepository(path=p).update_material("X", "X", "updated")
    rows = {r[0]: r[1] for r in MaterialRepository(path=p).load_materials()}
    assert rows["X"] == "updated"


# --------------------------------------------------------------------------- #
# Atomic write
# --------------------------------------------------------------------------- #


def test_atomic_write_no_tmp_file_remains(repo):
    repo.add_material("A", "a")
    assert not repo._path.with_suffix(".tmp").exists()


def test_atomic_write_file_is_valid_json_after_add(repo):
    repo.add_material("A", "a")
    data = json.loads(repo._path.read_text(encoding="utf-8"))
    assert data == [["A", "a"]]


def test_atomic_write_file_is_valid_json_after_delete(repo_with_data):
    repo_with_data.delete_material("1.4301BRUS-4.0")
    data = json.loads(repo_with_data._path.read_text(encoding="utf-8"))
    assert data == [["1.0037-2.0", "1.0037"]]


def test_atomic_write_file_is_valid_json_after_update(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "changed")
    data = json.loads(repo_with_data._path.read_text(encoding="utf-8"))
    assert any(row[1] == "changed" for row in data)


def test_stale_tmp_file_is_overwritten(repo):
    """A leftover .tmp file from a previous crash must not block a new write."""
    tmp = repo._path.with_suffix(".tmp")
    tmp.write_text("garbage", encoding="utf-8")
    repo.add_material("A", "a")
    assert not tmp.exists()
    assert repo.load_materials() == [["A", "a"]]


# --------------------------------------------------------------------------- #
# Corruption recovery
# --------------------------------------------------------------------------- #


def test_corrupt_json_load_returns_empty(tmp_path):
    p = tmp_path / "materials.json"
    p.write_text("NOT VALID JSON{{{{", encoding="utf-8")
    repo = MaterialRepository(path=p)
    assert repo.load_materials() == []


def test_corrupt_json_add_overwrites_with_new_data(tmp_path):
    p = tmp_path / "materials.json"
    p.write_text("NOT VALID JSON{{{{", encoding="utf-8")
    repo = MaterialRepository(path=p)
    repo.add_material("A", "a")
    assert repo.load_materials() == [["A", "a"]]


def test_empty_json_array_returns_empty(tmp_path):
    p = tmp_path / "materials.json"
    p.write_text("[]", encoding="utf-8")
    repo = MaterialRepository(path=p)
    assert repo.load_materials() == []


# --------------------------------------------------------------------------- #
# Path resolution
# --------------------------------------------------------------------------- #


def test_exe_dir_is_parent_of_argv0():
    expected = Path(sys.argv[0]).resolve().parent
    assert exe_dir() == expected


def test_default_path_is_under_exe_dir():
    expected = exe_dir() / MaterialRepository._DEFAULT_SUBDIR / MaterialRepository._DEFAULT_FILENAME
    assert expected == exe_dir() / "materials" / "materials.json"


def test_path_override_is_respected(tmp_path):
    p = tmp_path / "custom" / "store.json"
    p.parent.mkdir()
    repo = MaterialRepository(path=p)
    repo.add_material("A", "a")
    assert p.exists()
    assert not (tmp_path / "materials" / "materials.json").exists()


def test_repository_creates_parent_directories(tmp_path):
    p = tmp_path / "deep" / "nested" / "materials.json"
    repo = MaterialRepository(path=p)
    assert p.parent.is_dir()


# --------------------------------------------------------------------------- #
# Lock file
# --------------------------------------------------------------------------- #


def test_lock_file_created_in_same_directory(tmp_path):
    p = tmp_path / "materials.json"
    repo = MaterialRepository(path=p)
    repo.add_material("A", "a")
    assert (tmp_path / "materials.lock").exists()


# --------------------------------------------------------------------------- #
# Concurrent writes
# --------------------------------------------------------------------------- #


def test_concurrent_writes_do_not_corrupt(tmp_path):
    """Two threads adding different keys concurrently must each succeed."""
    p = _make_json(tmp_path)
    errors: list[Exception] = []

    def _worker(key: str):
        try:
            MaterialRepository(path=p).add_material(key, key.lower())
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=_worker, args=(f"KEY{i}",)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    keys = {r[0] for r in MaterialRepository(path=p).load_materials()}
    assert all(f"KEY{i}" in keys for i in range(10))


def test_concurrent_reads_are_consistent(tmp_path):
    """Parallel reads on the same file all return the same data."""
    p = _make_json(tmp_path, [["A", "a"], ["B", "b"]])
    results: list[list] = []

    def _read():
        results.append(MaterialRepository(path=p).load_materials())

    threads = [threading.Thread(target=_read) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r == [["A", "a"], ["B", "b"]] for r in results)


# --------------------------------------------------------------------------- #
# Migration from old CSV
# --------------------------------------------------------------------------- #


def test_migration_imports_old_csv(tmp_path, monkeypatch):
    """If no JSON exists but an old CSV is present, its data is imported."""
    csv_dir = tmp_path / "AppData" / "Local" / "NCRenamer"
    csv_dir.mkdir(parents=True)
    csv_path = csv_dir / "materials_new.csv"
    csv_path.write_text("1.4301BRUS-4.0\t1.4301 brus\n", encoding="utf-8")

    # Redirect Path.home() so the migration finder looks in tmp_path
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    json_path = tmp_path / "materials" / "materials.json"
    repo = MaterialRepository(path=json_path)

    materials = repo.load_materials()
    assert ["1.4301BRUS-4.0", "1.4301 brus"] in materials


def test_migration_skipped_when_json_exists(tmp_path, monkeypatch):
    """Existing JSON is never overwritten by migration."""
    csv_dir = tmp_path / "AppData" / "Local" / "NCRenamer"
    csv_dir.mkdir(parents=True)
    (csv_dir / "materials_new.csv").write_text("CSV_KEY\tcsv_val\n", encoding="utf-8")

    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    json_path = tmp_path / "materials.json"
    json_path.write_text(json.dumps([["JSON_KEY", "json_val"]]), encoding="utf-8")

    repo = MaterialRepository(path=json_path)
    keys = {r[0] for r in repo.load_materials()}
    assert "JSON_KEY" in keys
    assert "CSV_KEY" not in keys


def test_migration_graceful_when_no_csv(tmp_path, monkeypatch):
    """Starting fresh without any old CSV creates an empty JSON file."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    json_path = tmp_path / "materials" / "materials.json"
    repo = MaterialRepository(path=json_path)
    assert repo.load_materials() == []
    assert json_path.exists()


# --------------------------------------------------------------------------- #
# Shortcut-launch scenario (path resolution does not change)
# --------------------------------------------------------------------------- #


def test_path_unchanged_regardless_of_cwd(tmp_path, monkeypatch):
    """Changing CWD must not change the resolved path."""
    original = exe_dir()
    monkeypatch.chdir(tmp_path)
    assert exe_dir() == original
