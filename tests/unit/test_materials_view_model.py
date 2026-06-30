"""Unit tests for MaterialsViewModel — add, remove, get, texts."""

import pytest
from tests.conftest import StubMaterialRepository

from app.viewmodels.materials_view_model import MaterialsViewModel

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

TEXTS_EN = {
    "no_empty": "Material cannot be empty.",
    "material_exists": "Material already exists",
    "material_added": "Material added",
    "material_updated": "Material updated",
    "no_material_selected": "No material selected",
    "material_not_found": "Material not found",
    "material_removed": "Material removed",
}


@pytest.fixture
def vm():
    """MaterialsViewModel with an empty in-memory repo."""
    return MaterialsViewModel(
        app_instance=None,
        repo=StubMaterialRepository(),
        texts=TEXTS_EN,
    )


@pytest.fixture
def vm_with_data():
    """MaterialsViewModel pre-populated with one entry."""
    repo = StubMaterialRepository([["1.4301BRUS-4.0", "1.4301 brus"]])
    return MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)


# --------------------------------------------------------------------------- #
# get_materials
# --------------------------------------------------------------------------- #


def test_get_materials_returns_empty_list_for_empty_repo(vm):
    assert vm.get_materials() == []


def test_get_materials_returns_all_entries(vm_with_data):
    materials = vm_with_data.get_materials()
    assert len(materials) == 1
    assert materials[0] == ["1.4301BRUS-4.0", "1.4301 brus"]


# --------------------------------------------------------------------------- #
# add_material
# --------------------------------------------------------------------------- #


def test_add_material_success_returns_true_and_message(vm):
    success, msg = vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    assert success is True
    assert msg == "Material added"


def test_add_material_persists_entry(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    assert vm.get_materials() == [["1.4301BRUS-4.0", "1.4301 brus"]]


def test_add_material_rejects_empty_incorrect(vm):
    success, msg = vm.add_material("", "1.4301 brus")
    assert success is False
    assert msg == "Material cannot be empty."


def test_add_material_rejects_empty_correct(vm):
    success, msg = vm.add_material("1.4301BRUS-4.0", "")
    assert success is False
    assert msg == "Material cannot be empty."


def test_add_material_rejects_whitespace_only_incorrect(vm):
    success, msg = vm.add_material("   ", "1.4301 brus")
    assert success is False


def test_add_material_rejects_whitespace_only_correct(vm):
    success, msg = vm.add_material("1.4301BRUS-4.0", "   ")
    assert success is False


def test_add_material_strips_whitespace_before_storing(vm):
    vm.add_material("  1.4301BRUS-4.0  ", "  1.4301 brus  ")
    keys = [row[0] for row in vm.get_materials()]
    assert "1.4301BRUS-4.0" in keys


def test_add_material_rejects_duplicate(vm_with_data):
    success, msg = vm_with_data.add_material("1.4301BRUS-4.0", "anything")
    assert success is False
    assert msg == "Material already exists"


def test_add_material_does_not_increase_count_on_duplicate(vm_with_data):
    vm_with_data.add_material("1.4301BRUS-4.0", "anything")
    assert len(vm_with_data.get_materials()) == 1


# --------------------------------------------------------------------------- #
# update_material
# --------------------------------------------------------------------------- #


def test_update_material_success_returns_true_and_message(vm_with_data):
    success, msg = vm_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    assert success is True
    assert msg == "Material updated"


def test_update_material_changes_the_correct_value(vm_with_data):
    vm_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    rows = {r[0]: r[1] for r in vm_with_data.get_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 new"


def test_update_material_renames_incorrect_key(vm_with_data):
    vm_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-NEW", "1.4301 new")
    rows = {r[0]: r[1] for r in vm_with_data.get_materials()}
    assert "1.4301BRUS-NEW" in rows
    assert "1.4301BRUS-4.0" not in rows


def test_update_material_not_found_returns_false(vm):
    success, msg = vm.update_material("NONEXISTENT", "NONEXISTENT", "anything")
    assert success is False
    assert msg == "Material not found"


def test_update_material_rejects_empty_incorrect(vm_with_data):
    success, msg = vm_with_data.update_material("", "", "1.4301 new")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_material_rejects_empty_new_incorrect(vm_with_data):
    success, msg = vm_with_data.update_material("1.4301BRUS-4.0", "", "1.4301 new")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_material_rejects_empty_new_correct(vm_with_data):
    success, msg = vm_with_data.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_material_rejects_whitespace_only(vm_with_data):
    success, _ = vm_with_data.update_material("   ", "   ", "1.4301 new")
    assert success is False


# --------------------------------------------------------------------------- #
# remove_material
# --------------------------------------------------------------------------- #


def test_remove_material_success_returns_true_and_message(vm_with_data):
    success, msg = vm_with_data.remove_material("1.4301BRUS-4.0")
    assert success is True
    assert msg == "Material removed"


def test_remove_material_actually_removes_entry(vm_with_data):
    vm_with_data.remove_material("1.4301BRUS-4.0")
    assert vm_with_data.get_materials() == []


def test_remove_material_not_found_returns_false(vm):
    success, msg = vm.remove_material("NONEXISTENT")
    assert success is False
    assert msg == "Material not found"


def test_remove_material_empty_string_returns_false(vm):
    success, msg = vm.remove_material("")
    assert success is False
    assert msg == "No material selected"


def test_remove_material_whitespace_only_returns_false(vm):
    success, msg = vm.remove_material("   ")
    assert success is False


# --------------------------------------------------------------------------- #
# update_texts
# --------------------------------------------------------------------------- #


def test_update_texts_replaces_text_dict(vm):
    new_texts = {"material_added": "Pridano"}
    vm.update_texts(new_texts)
    assert vm.texts == new_texts


def test_update_texts_none_gives_empty_dict(vm):
    vm.update_texts(None)
    assert vm.texts == {}


def test_updated_texts_used_in_subsequent_add(vm):
    vm.update_texts({"material_added": "Pridano", "no_empty": "Prazdne"})
    _, msg = vm.add_material("A", "B")
    assert msg == "Pridano"
