# tests/unit/test_material_repository.py
"""Unit tests for MaterialRepository CRUD operations."""

import pytest

from app.models.material_repository import MaterialRepository

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def repo(tmp_path) -> MaterialRepository:
    """Fresh repository backed by an empty temp CSV."""
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("", encoding="utf-8")
    return MaterialRepository(csv_path=csv_file)


@pytest.fixture
def repo_with_data(tmp_path) -> MaterialRepository:
    """Repository pre-loaded with two entries."""
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text(
        "1.4301BRUS-4.0\t1.4301 brus\n1.0037-2.0\t1.0037\n",
        encoding="utf-8",
    )
    return MaterialRepository(csv_path=csv_file)


# --------------------------------------------------------------------------- #
# add_material + load_materials
# --------------------------------------------------------------------------- #


def test_add_and_load_material(repo):
    repo.add_material("1.4301BRUS-4.0", "1.4301 brus")
    assert repo.load_materials() == [["1.4301BRUS-4.0", "1.4301 brus"]]


def test_add_material_returns_true_on_success(repo):
    assert repo.add_material("1.4301BRUS-4.0", "1.4301 brus") is True


def test_add_material_strips_whitespace(repo):
    repo.add_material("  1.4301  ", "  1.4301 brus  ")
    loaded = repo.load_materials()
    assert loaded[0] == ["1.4301", "1.4301 brus"]


def test_add_material_prevents_duplicate(repo):
    repo.add_material("1.4301BRUS-4.0", "1.4301 brus")
    result = repo.add_material("1.4301BRUS-4.0", "something else")
    assert result is False


def test_add_material_duplicate_does_not_change_existing_entry(repo):
    repo.add_material("1.4301BRUS-4.0", "1.4301 brus")
    repo.add_material("1.4301BRUS-4.0", "different")
    assert repo.load_materials() == [["1.4301BRUS-4.0", "1.4301 brus"]]


def test_add_multiple_materials(repo):
    repo.add_material("A", "a")
    repo.add_material("B", "b")
    assert len(repo.load_materials()) == 2


# --------------------------------------------------------------------------- #
# delete_material
# --------------------------------------------------------------------------- #


def test_delete_material_removes_entry(repo_with_data):
    repo_with_data.delete_material("1.4301BRUS-4.0")
    keys = [row[0] for row in repo_with_data.load_materials()]
    assert "1.4301BRUS-4.0" not in keys


def test_delete_material_returns_true_on_success(repo_with_data):
    assert repo_with_data.delete_material("1.4301BRUS-4.0") is True


def test_delete_material_returns_false_when_not_found(repo_with_data):
    assert repo_with_data.delete_material("NONEXISTENT") is False


def test_delete_material_preserves_remaining_entries(repo_with_data):
    repo_with_data.delete_material("1.4301BRUS-4.0")
    remaining = repo_with_data.load_materials()
    assert remaining == [["1.0037-2.0", "1.0037"]]


def test_delete_material_strips_whitespace_before_comparing(repo_with_data):
    assert repo_with_data.delete_material("  1.4301BRUS-4.0  ") is True


# --------------------------------------------------------------------------- #
# update_material
# --------------------------------------------------------------------------- #


def test_update_material_changes_correct_value(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 new"


def test_update_material_returns_true_on_success(repo_with_data):
    assert (
        repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
        is True
    )


def test_update_material_returns_false_when_key_not_found(repo_with_data):
    assert (
        repo_with_data.update_material("NONEXISTENT", "NONEXISTENT", "anything")
        is False
    )


def test_update_material_preserves_other_entries(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.0037-2.0"] == "1.0037"


def test_update_material_strips_whitespace(repo_with_data):
    repo_with_data.update_material(
        "  1.4301BRUS-4.0  ", "1.4301BRUS-4.0", "  1.4301 new  "
    )
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 new"


def test_update_material_persists_to_csv(tmp_path):
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("1.4301BRUS-4.0\t1.4301 brus\n", encoding="utf-8")
    repo = MaterialRepository(csv_path=csv_file)
    repo.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 updated")
    repo2 = MaterialRepository(csv_path=csv_file)
    rows = {r[0]: r[1] for r in repo2.load_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 updated"


def test_update_material_renames_incorrect_key(repo_with_data):
    repo_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-NEW", "1.4301 new")
    rows = {r[0]: r[1] for r in repo_with_data.load_materials()}
    assert "1.4301BRUS-NEW" in rows
    assert "1.4301BRUS-4.0" not in rows
    assert rows["1.4301BRUS-NEW"] == "1.4301 new"


# --------------------------------------------------------------------------- #
# load_materials — edge cases
# --------------------------------------------------------------------------- #


def test_load_materials_returns_empty_for_empty_file(repo):
    assert repo.load_materials() == []


def test_load_materials_returns_empty_after_file_deleted(tmp_path):
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("A\tB\n", encoding="utf-8")
    r = MaterialRepository(csv_path=csv_file)
    csv_file.unlink()
    assert r.load_materials() == []


def test_load_materials_skips_rows_with_fewer_than_two_columns(tmp_path):
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("only_one_column\n1.4301\t1.4301 brus\n", encoding="utf-8")
    r = MaterialRepository(csv_path=csv_file)
    loaded = r.load_materials()
    assert loaded == [["1.4301", "1.4301 brus"]]
