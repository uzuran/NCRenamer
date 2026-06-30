"""Unit tests for AddMaterialFrame CRUD state-machine logic.

CTk widgets require a Tk display, so we do NOT instantiate AddMaterialFrame
directly.  Instead we test the pure-logic helpers via a lightweight fake frame
that replaces CTk with plain Python objects — and we test ViewModel contracts
directly.
"""

from __future__ import annotations

import pytest
from tests.conftest import StubMaterialRepository

from app.viewmodels.materials_view_model import MaterialsViewModel

# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #

TEXTS = {
    "no_empty": "Material cannot be empty.",
    "material_exists": "Material already exists",
    "material_added": "Material added",
    "material_updated": "Material updated",
    "no_material_selected": "No material selected",
    "material_not_found": "Material not found",
    "material_removed": "Material removed",
    "update_material": "Update material",
    "cancel_edit": "Cancel edit",
}


@pytest.fixture
def vm():
    repo = StubMaterialRepository([["1.4301BRUS-4.0", "1.4301 brus"]])
    return MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS)


@pytest.fixture
def empty_vm():
    return MaterialsViewModel(
        app_instance=None, repo=StubMaterialRepository(), texts=TEXTS
    )


# --------------------------------------------------------------------------- #
# ViewModel contract: what the Update button triggers
# --------------------------------------------------------------------------- #


def test_update_material_returns_success_tuple(vm):
    success, msg = vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    assert success is True
    assert msg == "Material updated"


def test_update_material_value_is_changed(vm):
    vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    rows = {r[0]: r[1] for r in vm.get_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 new"


def test_update_material_not_found_returns_false(empty_vm):
    success, msg = empty_vm.update_material("NONEXISTENT", "NONEXISTENT", "anything")
    assert success is False
    assert msg == "Material not found"


def test_update_material_empty_correct_returns_false(vm):
    success, msg = vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_material_whitespace_correct_returns_false(vm):
    success, msg = vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "   ")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_material_empty_incorrect_returns_false(vm):
    success, msg = vm.update_material("", "", "1.4301 new")
    assert success is False
    assert msg == "Material cannot be empty."


def test_update_does_not_duplicate_entry(vm):
    vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 new")
    assert len(vm.get_materials()) == 1


def test_update_then_get_reflects_new_value(vm):
    vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "1.4301 v2")
    materials = vm.get_materials()
    assert any(r[1] == "1.4301 v2" for r in materials)


def test_update_strips_whitespace_from_new_correct(vm):
    vm.update_material("1.4301BRUS-4.0", "1.4301BRUS-4.0", "  1.4301 trimmed  ")
    rows = {r[0]: r[1] for r in vm.get_materials()}
    assert rows["1.4301BRUS-4.0"] == "1.4301 trimmed"


def test_multiple_entries_only_target_is_changed():
    repo = StubMaterialRepository([["A", "a"], ["B", "b"], ["C", "c"]])
    vm = MaterialsViewModel(app_instance=None, repo=repo, texts=TEXTS)
    vm.update_material("B", "B", "b_updated")
    rows = {r[0]: r[1] for r in vm.get_materials()}
    assert rows["A"] == "a"
    assert rows["B"] == "b_updated"
    assert rows["C"] == "c"


# --------------------------------------------------------------------------- #
# Frame state-machine logic (no Tk, no display)
# --------------------------------------------------------------------------- #


class _FakeEntry:
    """Minimal stand-in for ctk.CTkEntry."""

    def __init__(self):
        self._text = ""
        self._state = "normal"

    def get(self):
        return self._text

    def delete(self, start, end):
        self._text = ""

    def insert(self, index, value):
        self._text = value

    def configure(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs["state"]

    @property
    def state(self):
        return self._state


class _FakeButton:
    """Minimal stand-in for ctk.CTkButton."""

    def __init__(self):
        self._state = "normal"

    def configure(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs["state"]

    @property
    def state(self):
        return self._state


class FakeAddMaterialFrame:
    """
    Pure-Python re-implementation of AddMaterialFrame's state machine.

    Mirrors _reset_edit_state, _deselect, on_tree_select, add_material, and
    update_selected_material without any CTk or Tk dependency.
    """

    def __init__(self, view_model):
        self.view_model = view_model
        self._editing_incorrect: str | None = None
        self.incorrect_entry = _FakeEntry()
        self.correct_entry = _FakeEntry()
        self.update_button = _FakeButton()
        self.update_button.configure(state="disabled")
        self.cancel_button = _FakeButton()
        self.cancel_button.configure(state="disabled")
        self.add_button = _FakeButton()
        self.last_flash: tuple[str, str] | None = None

    # mirrors the real frame ──────────────────────────────────────────

    def _reset_edit_state(self):
        """Return UI to add mode. Does NOT change treeview selection."""
        self._editing_incorrect = None
        self.incorrect_entry.configure(state="normal")
        self.incorrect_entry.delete(0, "end")
        self.correct_entry.delete(0, "end")
        self.update_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.add_button.configure(state="normal")

    def _deselect(self):
        """In the fake, directly resets edit state (no real treeview)."""
        self._reset_edit_state()

    def on_tree_select(self, incorrect: str, correct: str):
        """Simulate a treeview row selection."""
        self._editing_incorrect = incorrect
        self.incorrect_entry.delete(0, "end")
        self.incorrect_entry.insert(0, incorrect)
        self.correct_entry.delete(0, "end")
        self.correct_entry.insert(0, correct)
        self.update_button.configure(state="normal")
        self.cancel_button.configure(state="normal")
        self.add_button.configure(state="disabled")

    def update_selected_material(self):
        if not self._editing_incorrect:
            return False, ""
        new_incorrect = self.incorrect_entry.get()
        new_correct = self.correct_entry.get()
        success, message = self.view_model.update_material(
            self._editing_incorrect, new_incorrect, new_correct
        )
        if success:
            self._deselect()
        self.last_flash = (message, "green" if success else "red")
        return success, message

    def add_material(self):
        # Read entries FIRST — _reset_edit_state would clear them if called here.
        incorrect = self.incorrect_entry.get()
        correct = self.correct_entry.get()
        success, message = self.view_model.add_material(incorrect, correct)
        if success:
            self.incorrect_entry.delete(0, "end")
            self.correct_entry.delete(0, "end")
        self.last_flash = (message, "green" if success else "red")
        return success, message


# --------------------------------------------------------------------------- #
# FakeAddMaterialFrame: initial state
# --------------------------------------------------------------------------- #


@pytest.fixture
def frame(vm):
    return FakeAddMaterialFrame(vm)


@pytest.fixture
def empty_frame(empty_vm):
    return FakeAddMaterialFrame(empty_vm)


def test_initial_editing_incorrect_is_none(frame):
    assert frame._editing_incorrect is None


def test_initial_update_button_is_disabled(frame):
    assert frame.update_button.state == "disabled"


def test_initial_add_button_is_enabled(frame):
    assert frame.add_button.state == "normal"


def test_initial_incorrect_entry_is_editable(frame):
    assert frame.incorrect_entry.state == "normal"


def test_initial_cancel_button_is_disabled(frame):
    assert frame.cancel_button.state == "disabled"


# --------------------------------------------------------------------------- #
# on_tree_select
# --------------------------------------------------------------------------- #


def test_on_tree_select_sets_editing_incorrect(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame._editing_incorrect == "1.4301BRUS-4.0"


def test_on_tree_select_fills_entries(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame.incorrect_entry.get() == "1.4301BRUS-4.0"
    assert frame.correct_entry.get() == "1.4301 brus"


def test_on_tree_select_leaves_incorrect_entry_editable(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame.incorrect_entry.state == "normal"


def test_on_tree_select_enables_update_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame.update_button.state == "normal"


def test_on_tree_select_enables_cancel_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame.cancel_button.state == "normal"


def test_on_tree_select_disables_add_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    assert frame.add_button.state == "disabled"


# --------------------------------------------------------------------------- #
# _reset_edit_state
# --------------------------------------------------------------------------- #


def test_reset_clears_editing_incorrect(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame._editing_incorrect is None


def test_reset_incorrect_entry_stays_editable(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame.incorrect_entry.state == "normal"


def test_reset_disables_update_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame.update_button.state == "disabled"


def test_reset_disables_cancel_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame.cancel_button.state == "disabled"


def test_reset_re_enables_add_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame.add_button.state == "normal"


def test_reset_clears_entries(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._reset_edit_state()
    assert frame.incorrect_entry.get() == ""
    assert frame.correct_entry.get() == ""


# --------------------------------------------------------------------------- #
# _deselect
# --------------------------------------------------------------------------- #


def test_deselect_clears_editing_incorrect(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._deselect()
    assert frame._editing_incorrect is None


def test_deselect_re_enables_add_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._deselect()
    assert frame.add_button.state == "normal"


def test_deselect_disables_update_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._deselect()
    assert frame.update_button.state == "disabled"


def test_deselect_disables_cancel_button(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._deselect()
    assert frame.cancel_button.state == "disabled"


def test_deselect_clears_entries(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame._deselect()
    assert frame.incorrect_entry.get() == ""
    assert frame.correct_entry.get() == ""


# --------------------------------------------------------------------------- #
# update_selected_material via FakeAddMaterialFrame
# --------------------------------------------------------------------------- #


def test_update_selected_returns_true_on_success(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame.correct_entry.delete(0, "end")
    frame.correct_entry.insert(0, "1.4301 new")
    success, _ = frame.update_selected_material()
    assert success is True


def test_update_selected_resets_state_on_success(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame.correct_entry.delete(0, "end")
    frame.correct_entry.insert(0, "1.4301 new")
    frame.update_selected_material()
    assert frame._editing_incorrect is None
    assert frame.update_button.state == "disabled"
    assert frame.add_button.state == "normal"


def test_update_selected_no_op_when_nothing_selected(frame):
    success, msg = frame.update_selected_material()
    assert success is False
    assert msg == ""


def test_update_selected_shows_error_flash_on_failure(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame.correct_entry.delete(0, "end")
    frame.update_selected_material()
    assert frame.last_flash is not None
    assert frame.last_flash[1] == "red"


def test_update_selected_shows_green_flash_on_success(frame):
    frame.on_tree_select("1.4301BRUS-4.0", "1.4301 brus")
    frame.correct_entry.delete(0, "end")
    frame.correct_entry.insert(0, "1.4301 new")
    frame.update_selected_material()
    assert frame.last_flash is not None
    assert frame.last_flash[1] == "green"


# --------------------------------------------------------------------------- #
# add_material — regression: entries must be read BEFORE any state change
# --------------------------------------------------------------------------- #


def test_add_material_with_typed_values_succeeds(empty_frame):
    """Regression: add must read entry values, not get empty string after reset."""
    empty_frame.incorrect_entry.insert(0, "NEW-CODE")
    empty_frame.correct_entry.insert(0, "new value")
    success, _ = empty_frame.add_material()
    assert success is True


def test_add_material_clears_entries_on_success(empty_frame):
    empty_frame.incorrect_entry.insert(0, "NEW-CODE")
    empty_frame.correct_entry.insert(0, "new value")
    empty_frame.add_material()
    assert empty_frame.incorrect_entry.get() == ""
    assert empty_frame.correct_entry.get() == ""


def test_add_material_preserves_entries_on_failure(frame):
    """On failure (e.g. duplicate), entries must NOT be cleared."""
    frame.incorrect_entry.insert(0, "1.4301BRUS-4.0")  # already exists
    frame.correct_entry.insert(0, "1.4301 brus")
    frame.add_material()
    assert frame.incorrect_entry.get() == "1.4301BRUS-4.0"
    assert frame.correct_entry.get() == "1.4301 brus"


def test_add_material_shows_green_flash_on_success(empty_frame):
    empty_frame.incorrect_entry.insert(0, "NEW-CODE")
    empty_frame.correct_entry.insert(0, "new value")
    empty_frame.add_material()
    assert empty_frame.last_flash is not None
    assert empty_frame.last_flash[1] == "green"


def test_add_material_shows_red_flash_on_failure(frame):
    frame.incorrect_entry.insert(0, "1.4301BRUS-4.0")
    frame.correct_entry.insert(0, "1.4301 brus")
    frame.add_material()
    assert frame.last_flash is not None
    assert frame.last_flash[1] == "red"


def test_add_material_does_not_add_when_entries_empty(empty_frame):
    success, msg = empty_frame.add_material()
    assert success is False
    assert msg == "Material cannot be empty."
