"""
Integration tests for MaterialsViewModel + real MaterialRepository.

These tests exercise the full add / remove / load cycle against an actual
temp CSV file, verifying that ViewModel logic and repository persistence
work together correctly end-to-end.
"""

import pytest

from app.models.material_repository import MaterialRepository
from app.viewmodels.materials_view_model import MaterialsViewModel

TEXTS_EN = {
    "no_empty": "Material cannot be empty.",
    "material_exists": "Material already exists",
    "material_added": "Material added",
    "no_material_selected": "No material selected",
    "material_not_found": "Material not found",
    "material_removed": "Material removed",
}


@pytest.fixture
def repo(tmp_path) -> MaterialRepository:
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("", encoding="utf-8")
    return MaterialRepository(csv_path=csv_file)


@pytest.fixture
def vm(repo) -> MaterialsViewModel:
    return MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)


# --------------------------------------------------------------------------- #
# Full CRUD cycle
# --------------------------------------------------------------------------- #


def test_add_and_retrieve_material(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    materials = vm.get_materials()
    assert ["1.4301BRUS-4.0", "1.4301 brus"] in materials


def test_added_material_persists_across_get_calls(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    vm.add_material("1.0037-2.0", "1.0037")
    assert len(vm.get_materials()) == 2


def test_remove_material_and_verify_gone(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    vm.remove_material("1.4301BRUS-4.0")
    keys = [row[0] for row in vm.get_materials()]
    assert "1.4301BRUS-4.0" not in keys


def test_get_materials_empty_on_fresh_repo(vm):
    assert vm.get_materials() == []


def test_add_duplicate_not_stored_twice(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    vm.add_material("1.4301BRUS-4.0", "something else")
    assert len(vm.get_materials()) == 1


def test_add_multiple_then_remove_one_preserves_rest(vm):
    vm.add_material("A", "a")
    vm.add_material("B", "b")
    vm.add_material("C", "c")
    vm.remove_material("B")
    keys = [row[0] for row in vm.get_materials()]
    assert "A" in keys
    assert "B" not in keys
    assert "C" in keys


def test_remove_nonexistent_does_not_affect_existing_data(vm):
    vm.add_material("1.4301BRUS-4.0", "1.4301 brus")
    vm.remove_material("NONEXISTENT")
    assert len(vm.get_materials()) == 1


# --------------------------------------------------------------------------- #
# Persistence — a second ViewModel instance reading same CSV
# --------------------------------------------------------------------------- #


def test_data_visible_to_second_viewmodel_instance(repo):
    vm1 = MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)
    vm1.add_material("1.4301BRUS-4.0", "1.4301 brus")

    vm2 = MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)
    keys = [row[0] for row in vm2.get_materials()]
    assert "1.4301BRUS-4.0" in keys


def test_removal_visible_to_second_viewmodel_instance(repo):
    vm1 = MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)
    vm1.add_material("1.4301BRUS-4.0", "1.4301 brus")
    vm1.remove_material("1.4301BRUS-4.0")

    vm2 = MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS_EN)
    assert vm2.get_materials() == []
