"""Unit tests for MainViewModel — uses stubs for all external dependencies."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.viewmodels.main_view_model import MainViewModel
from tests.conftest import StubEmailModel, StubFormatterModel


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def vm():
    """MainViewModel with zeroed stubs — no filesystem access."""
    return MainViewModel(
        email_model=StubEmailModel(counter=0),
        formatter_model=StubFormatterModel(),
    )


@pytest.fixture
def vm_with_files(tmp_path):
    """MainViewModel with two pre-selected NC files on disk."""
    f1 = tmp_path / "4039-100.NC"
    f2 = tmp_path / "4039-101.NC"
    f1.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
    f2.write_text("L1\nL2\nL3\n(MA/1.0037)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(),
    )
    vm.select_files([str(f1), str(f2)])
    return vm, f1, f2


# --------------------------------------------------------------------------- #
# File selection
# --------------------------------------------------------------------------- #

def test_file_paths_empty_on_init(vm):
    assert vm.file_paths == []


def test_select_files_from_list(vm, tmp_path):
    p = tmp_path / "test.NC"
    p.touch()
    vm.select_files([str(p)])
    assert len(vm.file_paths) == 1


def test_select_files_from_tuple(vm, tmp_path):
    p = tmp_path / "test.NC"
    p.touch()
    # filedialog.askopenfilenames returns a tuple
    vm.select_files((str(p),))
    assert len(vm.file_paths) == 1


def test_select_files_converts_strings_to_path_objects(vm, tmp_path):
    p = tmp_path / "test.NC"
    p.touch()
    vm.select_files([str(p)])
    assert all(isinstance(f, Path) for f in vm.file_paths)


def test_select_files_replaces_previous_selection(vm, tmp_path):
    p1 = tmp_path / "a.NC"
    p2 = tmp_path / "b.NC"
    p1.touch()
    p2.touch()
    vm.select_files([str(p1)])
    vm.select_files([str(p2)])
    assert len(vm.file_paths) == 1
    assert vm.file_paths[0].name == "b.NC"


def test_select_files_multiple(vm, tmp_path):
    files = [tmp_path / f"{i}.NC" for i in range(5)]
    for f in files:
        f.touch()
    vm.select_files([str(f) for f in files])
    assert len(vm.file_paths) == 5


# --------------------------------------------------------------------------- #
# Unselect files
# --------------------------------------------------------------------------- #

def test_unselect_files_clears_selection(vm_with_files):
    vm, _, _ = vm_with_files
    vm.unselect_files()
    assert vm.file_paths == []


def test_unselect_files_returns_count_of_removed_files(vm_with_files):
    vm, _, _ = vm_with_files
    assert vm.unselect_files() == 2


def test_unselect_files_when_empty_returns_zero(vm):
    assert vm.unselect_files() == 0


# --------------------------------------------------------------------------- #
# Email counter
# --------------------------------------------------------------------------- #

def test_email_counter_reads_from_model(vm):
    assert vm.email_counter == 0


def test_email_counter_reflects_model_state():
    m = StubEmailModel(counter=42)
    v = MainViewModel(email_model=m, formatter_model=StubFormatterModel())
    assert v.email_counter == 42


def test_increment_email_counter_increases_by_one(vm):
    vm.increment_email_counter()
    assert vm.email_counter == 1


def test_increment_email_counter_multiple_times(vm):
    vm.increment_email_counter()
    vm.increment_email_counter()
    vm.increment_email_counter()
    assert vm.email_counter == 3


def test_reset_email_counter_sets_to_zero(vm):
    vm.increment_email_counter()
    vm.increment_email_counter()
    vm.reset_email_counter()
    assert vm.email_counter == 0


# --------------------------------------------------------------------------- #
# get_mailto_url
# --------------------------------------------------------------------------- #

def test_get_mailto_url_starts_with_mailto(vm):
    url = vm.get_mailto_url()
    assert url.startswith("mailto:")


def test_get_mailto_url_contains_recipient():
    m = StubEmailModel(counter=0)
    v = MainViewModel(email_model=m, formatter_model=StubFormatterModel())
    assert MainViewModel.BUG_REPORT_EMAIL in v.get_mailto_url()


def test_get_mailto_url_contains_counter_value(vm):
    vm.increment_email_counter()
    vm.increment_email_counter()
    url = vm.get_mailto_url()
    assert "2" in url


def test_get_mailto_url_url_encodes_subject(vm):
    url = vm.get_mailto_url()
    # spaces must be percent-encoded; the subject contains "Report bug_N"
    assert " " not in url


# --------------------------------------------------------------------------- #
# process_single_file
# --------------------------------------------------------------------------- #

def test_process_single_file_returns_three_tuple(tmp_path):
    nc = tmp_path / "4039-100.NC"
    nc.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(changed=False),
    )
    result = vm.process_single_file(nc)
    assert len(result) == 3


def test_process_single_file_filename_is_stem_with_extension(tmp_path):
    nc = tmp_path / "4039-100.NC"
    nc.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(),
    )
    name, _, _ = vm.process_single_file(nc)
    assert name == "4039-100.NC"


def test_process_single_file_changed_flag_true(tmp_path):
    nc = tmp_path / "test.NC"
    nc.write_text("L1\nL2\nL3\n(MA/1.4301BRUS-4.0)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(changed=True, material="1.4301 brus"),
    )
    _, changed, _ = vm.process_single_file(nc)
    assert changed is True


def test_process_single_file_changed_flag_false(tmp_path):
    nc = tmp_path / "test.NC"
    nc.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(changed=False),
    )
    _, changed, _ = vm.process_single_file(nc)
    assert changed is False


def test_process_single_file_material_is_none_when_line4_absent(tmp_path):
    nc = tmp_path / "test.NC"
    nc.write_text("L1\nL2\nL3\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(line_4=None),
    )
    _, _, material = vm.process_single_file(nc)
    assert material is None


def test_process_single_file_returns_material_string(tmp_path):
    nc = tmp_path / "test.NC"
    nc.write_text("L1\nL2\nL3\n(MA/1.4301)\nL5\n", encoding="utf-8")
    vm = MainViewModel(
        email_model=StubEmailModel(),
        formatter_model=StubFormatterModel(material="1.4301"),
    )
    _, _, material = vm.process_single_file(nc)
    assert material == "1.4301"
