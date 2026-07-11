"""Tests for BurnViewModel duplicate-program validation."""

from pathlib import Path
from unittest.mock import patch

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.table_status import TableStatus
from app.burn_table.viewmodels.burn_view_model import BurnViewModel


def _make_vm() -> BurnViewModel:
    """Return a BurnViewModel with a fake loaded table (no I/O)."""
    vm = BurnViewModel()
    vm._table_path = Path("/fake/table.xls")
    vm._records = [
        BurnRecord(program_number="6670-18"),
        BurnRecord(program_number="4041-05"),
    ]
    vm._status = TableStatus(used_rows=2, free_rows=36, is_full=False, warning="")
    return vm


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


class TestLoadAndAppendBatchDuplicates:
    def test_duplicate_sets_popup_message(self):
        vm = _make_vm()
        fake_record = BurnRecord(program_number="6670-18")

        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/6670-18.NC")])

        assert vm.popup_message is not None
        assert "6670-18" in vm.popup_message

    def test_duplicate_not_appended(self):
        vm = _make_vm()
        initial_count = len(vm._records)
        fake_record = BurnRecord(program_number="6670-18")

        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/6670-18.NC")])

        assert len(vm._records) == initial_count

    def test_unique_record_appended_alongside_duplicate(self):
        vm = _make_vm()
        fake_dup = BurnRecord(program_number="6670-18")
        fake_new = BurnRecord(program_number="9999-01")

        with (
            patch.object(
                vm._recorder, "record_from_paths", side_effect=[fake_dup, fake_new]
            ),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
        ):
            vm.load_and_append_batch(
                [
                    Path("/nc/6670-18.NC"),
                    Path("/nc/9999-01.NC"),
                ]
            )

        assert vm.popup_message is not None
        assert len(vm._records) == 3  # 2 original + 1 new

    def test_clear_popup_resets_message(self):
        vm = _make_vm()
        vm._popup_message = "test warning"
        vm.clear_popup()
        assert vm.popup_message is None


class TestCrossSheetDuplicates:
    def _make_peer(self, program_numbers: list[str]) -> BurnViewModel:
        peer = BurnViewModel()
        peer._records = [BurnRecord(program_number=p) for p in program_numbers]
        return peer

    def test_cross_sheet_duplicate_sets_popup(self):
        vm = _make_vm()
        peer = self._make_peer(["9999-01"])
        vm.set_peer_vm(peer)
        peer.set_peer_vm(vm)

        fake_record = BurnRecord(program_number="9999-01")
        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/9999-01.NC")])

        assert vm.popup_message is not None
        assert "9999-01" in vm.popup_message

    def test_cross_sheet_duplicate_not_appended(self):
        vm = _make_vm()
        peer = self._make_peer(["9999-01"])
        vm.set_peer_vm(peer)

        initial_count = len(vm._records)
        fake_record = BurnRecord(program_number="9999-01")
        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/9999-01.NC")])

        assert len(vm._records) == initial_count

    def test_cross_sheet_check_is_case_insensitive(self):
        vm = _make_vm()
        peer = self._make_peer(["9999-AA"])
        vm.set_peer_vm(peer)

        fake_record = BurnRecord(program_number="9999-aa")
        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/9999-aa.NC")])

        assert vm.popup_message is not None

    def test_no_peer_vm_skips_cross_sheet_check(self):
        vm = _make_vm()
        # No peer set — should behave as before

        fake_record = BurnRecord(program_number="9999-01")
        with (
            patch.object(vm._recorder, "record_from_paths", return_value=fake_record),
            patch.object(vm._writer, "write_record_at_row", return_value=None),
        ):
            vm.load_and_append_batch([Path("/nc/9999-01.NC")])

        assert len(vm._records) == 3  # appended successfully

    def test_same_sheet_duplicate_takes_priority_over_cross_sheet(self):
        vm = _make_vm()
        peer = self._make_peer(["6670-18"])  # also in peer
        vm.set_peer_vm(peer)

        fake_record = BurnRecord(program_number="6670-18")  # already in vm._records
        with patch.object(vm._recorder, "record_from_paths", return_value=fake_record):
            vm.load_and_append_batch([Path("/nc/6670-18.NC")])

        # Should show same-sheet warning (caught first)
        assert vm.popup_message is not None
        assert "6670-18" in vm.popup_message


class TestGetExistingPrograms:
    def test_returns_program_numbers_from_file(self):
        from app.burn_table.services.excel_reader import ExcelReader

        reader = ExcelReader()
        records = [
            BurnRecord(program_number="6670-18"),
            BurnRecord(program_number="4041-05"),
            BurnRecord(program_number=""),  # empty — should be excluded
        ]
        with patch.object(reader, "read_all", return_value=records):
            result = reader.get_existing_programs(Path("/fake/table.xls"))

        assert result == ["6670-18", "4041-05"]

    def test_returns_empty_list_on_error(self):
        from app.burn_table.services.excel_reader import ExcelReader

        reader = ExcelReader()
        with patch.object(reader, "read_all", side_effect=OSError("not found")):
            result = reader.get_existing_programs(Path("/missing/table.xls"))

        assert result == []
