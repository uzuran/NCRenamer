"""Tests for BurnViewModel duplicate-program validation.

Two layers are tested:

1. ``validate_unique_program`` — pure predicate (unchanged).

2. ``load_and_append_batch`` duplicate handling — the callback-based
   confirmation system:

   * When NO callback is registered (default) duplicates are silently
     rejected — backward-compatible behaviour for standalone / non-GUI use.

   * When a callback IS registered it is called with (program_number,
     sheet_name) once per duplicate.  Returning True means "Add anyway";
     returning False means "Cancel".

The tests use a lambda callback instead of a tkinter messagebox so they run
without a display.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.table_status import TableStatus
from app.burn_table.viewmodels.burn_view_model import BurnViewModel


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_vm() -> BurnViewModel:
    """Return a BurnViewModel with two pre-loaded records and a fake path."""
    vm = BurnViewModel()
    vm._table_path = Path("/fake/table.xls")
    vm._records = [
        BurnRecord(program_number="6670-18"),
        BurnRecord(program_number="4041-05"),
    ]
    vm._status = TableStatus(used_rows=2, free_rows=36, is_full=False, warning="")
    return vm


def _make_peer(*program_numbers: str) -> BurnViewModel:
    peer = BurnViewModel()
    peer._records = [BurnRecord(program_number=p) for p in program_numbers]
    return peer


def _load_single(vm: BurnViewModel, program_number: str) -> None:
    """Drive load_and_append_batch with a single fake record."""
    fake_record = BurnRecord(program_number=program_number)
    with (
        patch.object(vm._recorder, "record_from_paths", return_value=fake_record),
        patch.object(vm._writer, "write_record_at_row", return_value=None),
        patch.object(vm._writer, "write_empty_row", return_value=None),
    ):
        vm.load_and_append_batch([Path(f"/nc/{program_number}.NC")])


# ══════════════════════════════════════════════════════════════════════════════
# 1. validate_unique_program  (pure predicate — behaviour unchanged)
# ══════════════════════════════════════════════════════════════════════════════


class TestValidateUniqueProgram:
    def test_returns_true_for_new_program(self):
        vm = _make_vm()
        assert vm.validate_unique_program("9999-01") is True

    def test_returns_false_for_existing_program(self):
        vm = _make_vm()
        assert vm.validate_unique_program("6670-18") is False

    def test_returns_true_for_empty_program_number(self):
        vm = _make_vm()
        assert vm.validate_unique_program("") is True

    def test_case_insensitive_match(self):
        vm = BurnViewModel()
        vm._records = [BurnRecord(program_number="6670-AB")]
        assert vm.validate_unique_program("6670-ab") is False
        assert vm.validate_unique_program("6670-Ab") is False


# ══════════════════════════════════════════════════════════════════════════════
# 2. Same-sheet duplicate — no callback registered (default / silent reject)
# ══════════════════════════════════════════════════════════════════════════════


class TestSameSheetDuplicateNoCallback:
    def test_duplicate_not_appended(self):
        vm = _make_vm()
        initial_count = len(vm._records)
        _load_single(vm, "6670-18")
        assert len(vm._records) == initial_count

    def test_no_popup_message_set(self):
        """Confirmation dialog replaced the old warning popup; popup_message stays None."""
        vm = _make_vm()
        _load_single(vm, "6670-18")
        assert vm.popup_message is None

    def test_status_message_mentions_skipped(self):
        vm = _make_vm()
        _load_single(vm, "6670-18")
        assert "6670-18" in vm.message

    def test_unique_record_appended_even_when_duplicate_present(self):
        vm = _make_vm()
        fake_dup = BurnRecord(program_number="6670-18")
        fake_new = BurnRecord(program_number="9999-01")
        with (
            patch.object(
                vm._recorder, "record_from_paths", side_effect=[fake_dup, fake_new]
            ),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
            patch.object(vm._writer, "write_empty_row", return_value=None),
        ):
            vm.load_and_append_batch(
                [Path("/nc/6670-18.NC"), Path("/nc/9999-01.NC")]
            )
        assert len(vm._records) == 3  # 2 original + 1 new unique


# ══════════════════════════════════════════════════════════════════════════════
# 3. Same-sheet duplicate — callback registered
# ══════════════════════════════════════════════════════════════════════════════


class TestSameSheetDuplicateWithCallback:
    def test_confirm_yes_adds_record(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: True)   # always confirm
        _load_single(vm, "6670-18")
        assert len(vm._records) == 3   # duplicate allowed

    def test_confirm_no_skips_record(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: False)  # always cancel
        _load_single(vm, "6670-18")
        assert len(vm._records) == 2   # duplicate rejected

    def test_callback_receives_correct_program_number(self):
        vm = _make_vm()
        seen: list[str] = []
        vm.set_confirm_duplicate(lambda pn, sheet: seen.append(pn) or False)
        _load_single(vm, "6670-18")
        assert seen == ["6670-18"]

    def test_callback_receives_own_sheet_name(self):
        vm = _make_vm()
        vm._sheet_name = "Ocel"
        seen_sheet: list[str] = []
        vm.set_confirm_duplicate(lambda pn, sheet: seen_sheet.append(sheet) or False)
        _load_single(vm, "6670-18")
        assert seen_sheet == ["Ocel"]

    def test_no_popup_message_set_even_when_confirmed(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: True)
        _load_single(vm, "6670-18")
        assert vm.popup_message is None

    def test_duplicate_added_appears_in_display_rows(self):
        vm = _make_vm()
        vm._display_rows = list(vm._records)
        vm.set_confirm_duplicate(lambda pn, sheet: True)
        _load_single(vm, "6670-18")
        programs = [r.program_number for r in vm._display_rows if r is not None]
        assert programs.count("6670-18") == 2

    def test_callback_called_once_per_duplicate(self):
        vm = _make_vm()
        call_count = [0]
        def cb(pn, sheet):
            call_count[0] += 1
            return True
        vm.set_confirm_duplicate(cb)
        # Load same duplicate twice in one batch
        fake = BurnRecord(program_number="6670-18")
        with (
            patch.object(vm._recorder, "record_from_paths", side_effect=[fake, fake]),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
            patch.object(vm._writer, "write_empty_row", return_value=None),
        ):
            vm.load_and_append_batch(
                [Path("/nc/6670-18.NC"), Path("/nc/6670-18b.NC")]
            )
        # First occurrence: dup found → callback; second: dup found → callback again
        assert call_count[0] == 2


# ══════════════════════════════════════════════════════════════════════════════
# 4. Cross-sheet duplicate — no callback registered
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossSheetDuplicateNoCallback:
    def test_cross_sheet_duplicate_not_appended(self):
        vm = _make_vm()
        peer = _make_peer("9999-01")
        vm.set_peer_vm(peer)
        initial_count = len(vm._records)
        _load_single(vm, "9999-01")
        assert len(vm._records) == initial_count

    def test_no_popup_message_set(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        _load_single(vm, "9999-01")
        assert vm.popup_message is None

    def test_cross_sheet_check_is_case_insensitive(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-AA"))
        initial_count = len(vm._records)
        _load_single(vm, "9999-aa")
        assert len(vm._records) == initial_count

    def test_no_peer_vm_skips_cross_sheet_check(self):
        vm = _make_vm()
        # No peer set — record that would be a cross-sheet dup is added freely
        _load_single(vm, "9999-01")
        assert len(vm._records) == 3

    def test_same_sheet_duplicate_takes_priority_over_cross_sheet(self):
        """A program in both sheets is caught by the same-sheet check first."""
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("6670-18"))   # also in peer
        initial_count = len(vm._records)
        _load_single(vm, "6670-18")
        assert len(vm._records) == initial_count


# ══════════════════════════════════════════════════════════════════════════════
# 5. Cross-sheet duplicate — callback registered
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossSheetDuplicateWithCallback:
    def test_confirm_yes_adds_record(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        vm.set_confirm_duplicate(lambda pn, sheet: True)
        _load_single(vm, "9999-01")
        assert len(vm._records) == 3

    def test_confirm_no_skips_record(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        vm.set_confirm_duplicate(lambda pn, sheet: False)
        _load_single(vm, "9999-01")
        assert len(vm._records) == 2

    def test_callback_receives_peer_sheet_name(self):
        vm = _make_vm()
        peer = _make_peer("9999-01")
        peer._sheet_name = "Hliník"
        vm.set_peer_vm(peer)
        seen_sheet: list[str] = []
        vm.set_confirm_duplicate(lambda pn, sheet: seen_sheet.append(sheet) or False)
        _load_single(vm, "9999-01")
        assert seen_sheet == ["Hliník"]

    def test_callback_receives_correct_program_number(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        seen_pn: list[str] = []
        vm.set_confirm_duplicate(lambda pn, sheet: seen_pn.append(pn) or False)
        _load_single(vm, "9999-01")
        assert seen_pn == ["9999-01"]

    def test_no_popup_message_even_when_confirmed(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        vm.set_confirm_duplicate(lambda pn, sheet: True)
        _load_single(vm, "9999-01")
        assert vm.popup_message is None

    def test_cross_dup_added_appears_in_records(self):
        vm = _make_vm()
        vm.set_peer_vm(_make_peer("9999-01"))
        vm.set_confirm_duplicate(lambda pn, sheet: True)
        _load_single(vm, "9999-01")
        assert any(r.program_number == "9999-01" for r in vm._records)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Mixed batch — some duplicates confirmed, some cancelled, some unique
# ══════════════════════════════════════════════════════════════════════════════


class TestMixedBatch:
    def test_confirmed_dups_and_unique_both_added(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: True)

        records = [
            BurnRecord(program_number="6670-18"),  # same-sheet dup → confirmed
            BurnRecord(program_number="9999-01"),  # unique
        ]
        with (
            patch.object(vm._recorder, "record_from_paths", side_effect=records),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
            patch.object(vm._writer, "write_empty_row", return_value=None),
        ):
            vm.load_and_append_batch(
                [Path("/nc/6670-18.NC"), Path("/nc/9999-01.NC")]
            )

        assert len(vm._records) == 4   # 2 original + dup + unique

    def test_cancelled_dup_not_added_unique_is(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: False)

        records = [
            BurnRecord(program_number="6670-18"),  # dup → cancelled
            BurnRecord(program_number="9999-01"),  # unique
        ]
        with (
            patch.object(vm._recorder, "record_from_paths", side_effect=records),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
            patch.object(vm._writer, "write_empty_row", return_value=None),
        ):
            vm.load_and_append_batch(
                [Path("/nc/6670-18.NC"), Path("/nc/9999-01.NC")]
            )

        assert len(vm._records) == 3   # 2 original + unique only

    def test_separator_written_only_when_at_least_one_record_added(self):
        vm = _make_vm()
        vm.set_confirm_duplicate(lambda pn, sheet: False)  # cancel everything
        initial_display = len(vm._display_rows)
        _load_single(vm, "6670-18")   # dup, cancelled
        # display_rows must not grow (no separator inserted)
        assert len(vm._display_rows) == initial_display


# ══════════════════════════════════════════════════════════════════════════════
# 7. Misc: clear_popup, get_existing_programs (unchanged behaviour)
# ══════════════════════════════════════════════════════════════════════════════


class TestMisc:
    def test_clear_popup_resets_message(self):
        vm = _make_vm()
        vm._popup_message = "test warning"
        vm.clear_popup()
        assert vm.popup_message is None

    def test_set_confirm_duplicate_replaces_previous_callback(self):
        vm = _make_vm()
        calls: list[int] = []
        vm.set_confirm_duplicate(lambda pn, sheet: calls.append(1) or False)
        vm.set_confirm_duplicate(lambda pn, sheet: calls.append(2) or False)
        _load_single(vm, "6670-18")
        assert calls == [2]   # only the second callback was called

    def test_get_existing_programs_returns_program_numbers_from_file(self):
        from app.burn_table.services.excel_reader import ExcelReader

        reader = ExcelReader()
        records = [
            BurnRecord(program_number="6670-18"),
            BurnRecord(program_number="4041-05"),
            BurnRecord(program_number=""),   # empty — excluded
        ]
        with patch.object(reader, "read_all", return_value=records):
            result = reader.get_existing_programs(Path("/fake/table.xls"))

        assert result == ["6670-18", "4041-05"]

    def test_get_existing_programs_returns_empty_on_error(self):
        from app.burn_table.services.excel_reader import ExcelReader

        reader = ExcelReader()
        with patch.object(reader, "read_all", side_effect=OSError("not found")):
            result = reader.get_existing_programs(Path("/missing/table.xls"))

        assert result == []
