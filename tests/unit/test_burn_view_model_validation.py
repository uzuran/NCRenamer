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
    vm._status = TableStatus(used_rows=2, free_rows=32, is_full=False, warning="")
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
            patch.object(vm._writer, "append_record", return_value=3),
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
