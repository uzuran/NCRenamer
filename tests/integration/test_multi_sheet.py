"""Integration tests for the two-sheet (Ocel / Hliník) architecture.

Verifies:
- ensure_sheet_exists creates a second sheet when one doesn't exist
- Writing to sheet_index=1 does not affect sheet_index=0 data
- Reading from the correct sheet returns only that sheet's records
- FreeSlotDetector counts per-sheet correctly
- BurnViewModel with two VMs keeps data isolated between sheets
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.services.table_factory import TableFactory
from app.burn_table.viewmodels.burn_view_model import BurnViewModel


def _rec(program: str = "6670-18", date: str = "30.06.2026") -> BurnRecord:
    return BurnRecord(
        date=date,
        program_number=program,
        sheet_format="1.0037-5X1700X1500",
        sheet_count=1,
        total_time="00:21:51",
    )


@pytest.fixture(params=["table.xls", "table.xlsx"])
def single_sheet_file(request, tmp_path) -> Path:
    """File with only sheet 0 (Ocel) — simulates existing laser.xls before migration."""
    path: Path = tmp_path / str(request.param)
    TableFactory().create(path)
    return path


@pytest.fixture(params=["table.xls", "table.xlsx"])
def two_sheet_file(request, tmp_path) -> Path:
    """File with both sheets (Ocel + Hliník)."""
    path: Path = tmp_path / str(request.param)
    TableFactory().create(path)
    ExcelWriter(sheet_index=1).ensure_sheet_exists(path, "Hliník")
    ExcelWriter(sheet_index=1).update_header(path)
    return path


class TestEnsureSheetExists:
    def test_creates_second_sheet_when_missing(self, single_sheet_file):
        writer = ExcelWriter(sheet_index=1)
        created = writer.ensure_sheet_exists(single_sheet_file, "Hliník")
        assert created is True

    def test_sheet_count_increases_to_two(self, single_sheet_file):
        ExcelWriter(sheet_index=1).ensure_sheet_exists(single_sheet_file, "Hliník")
        if single_sheet_file.suffix == ".xls":
            import xlrd

            assert xlrd.open_workbook(str(single_sheet_file)).nsheets == 2
        else:
            import openpyxl

            assert len(openpyxl.load_workbook(single_sheet_file).worksheets) == 2

    def test_returns_false_when_sheet_already_exists(self, two_sheet_file):
        created = ExcelWriter(sheet_index=1).ensure_sheet_exists(
            two_sheet_file, "Hliník"
        )
        assert created is False

    def test_existing_sheet_zero_data_preserved(self, single_sheet_file):
        ExcelWriter(sheet_index=0).append_record(single_sheet_file, _rec("STEEL-01"))
        ExcelWriter(sheet_index=1).ensure_sheet_exists(single_sheet_file, "Hliník")
        records = ExcelReader(sheet_index=0).read_all(single_sheet_file)
        assert len(records) == 1
        assert records[0].program_number == "STEEL-01"

    def test_noop_when_index_0_and_file_has_one_sheet(self, single_sheet_file):
        """Sheet 0 already exists — ensure_sheet_exists must be a no-op."""
        created = ExcelWriter(sheet_index=0).ensure_sheet_exists(
            single_sheet_file, "Ocel"
        )
        assert created is False


class TestSheetIsolation:
    def test_write_to_sheet0_not_visible_in_sheet1(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        records_alu = ExcelReader(sheet_index=1).read_all(two_sheet_file)
        assert records_alu == []

    def test_write_to_sheet1_not_visible_in_sheet0(self, two_sheet_file):
        ExcelWriter(sheet_index=1).append_record(two_sheet_file, _rec("ALU-01"))
        records_steel = ExcelReader(sheet_index=0).read_all(two_sheet_file)
        assert records_steel == []

    def test_independent_records_on_each_sheet(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        ExcelWriter(sheet_index=1).append_record(two_sheet_file, _rec("ALU-01"))

        steel = ExcelReader(sheet_index=0).read_all(two_sheet_file)
        alu = ExcelReader(sheet_index=1).read_all(two_sheet_file)

        assert len(steel) == 1 and steel[0].program_number == "STEEL-01"
        assert len(alu) == 1 and alu[0].program_number == "ALU-01"

    def test_multiple_records_per_sheet(self, two_sheet_file):
        for i in range(3):
            ExcelWriter(sheet_index=0).append_record(
                two_sheet_file, _rec(f"STEEL-{i:02d}")
            )
        for i in range(5):
            ExcelWriter(sheet_index=1).append_record(
                two_sheet_file, _rec(f"ALU-{i:02d}")
            )

        assert len(ExcelReader(sheet_index=0).read_all(two_sheet_file)) == 3
        assert len(ExcelReader(sheet_index=1).read_all(two_sheet_file)) == 5

    def test_clear_sheet0_leaves_sheet1_intact(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        ExcelWriter(sheet_index=1).append_record(two_sheet_file, _rec("ALU-01"))

        ExcelWriter(sheet_index=0).clear_all_records(two_sheet_file)

        steel = ExcelReader(sheet_index=0).read_all(two_sheet_file)
        alu = ExcelReader(sheet_index=1).read_all(two_sheet_file)

        assert steel == []
        assert len(alu) == 1 and alu[0].program_number == "ALU-01"


class TestFreeSlotDetectorPerSheet:
    def test_each_sheet_has_independent_slot_count(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-02"))
        ExcelWriter(sheet_index=1).append_record(two_sheet_file, _rec("ALU-01"))

        steel_status = FreeSlotDetector(sheet_index=0).detect(two_sheet_file)
        alu_status = FreeSlotDetector(sheet_index=1).detect(two_sheet_file)

        assert steel_status.used_rows == 2
        assert alu_status.used_rows == 1

    def test_empty_sheet1_shows_38_free(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        alu_status = FreeSlotDetector(sheet_index=1).detect(two_sheet_file)
        assert alu_status.free_rows == 38


class TestBurnViewModelTwoSheets:
    """BurnViewModel with two instances targeting different sheets stays isolated."""

    def _vm(self, path: Path, sheet_index: int) -> BurnViewModel:
        """Create a BurnViewModel pointing to a real file but with mocked settings."""
        from app.burn_table.services.excel_reader import ExcelReader
        from app.burn_table.services.excel_writer import ExcelWriter
        from app.burn_table.services.free_slot_detector import FreeSlotDetector
        from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder
        from app.burn_table.viewmodels.print_manager import PrintManager

        vm = BurnViewModel(
            reader=ExcelReader(sheet_index=sheet_index),
            writer=ExcelWriter(sheet_index=sheet_index),
            detector=FreeSlotDetector(sheet_index=sheet_index),
            recorder=PerformanceRecorder(),
            print_manager=PrintManager(),
            sheet_name="Ocel" if sheet_index == 0 else "Hliník",
            settings_key="last_table_path"
            if sheet_index == 0
            else "last_table_path_alu",
        )
        vm.load_table(path)
        return vm

    def test_two_vms_load_independent_records(self, two_sheet_file):
        ExcelWriter(sheet_index=0).append_record(two_sheet_file, _rec("STEEL-01"))
        ExcelWriter(sheet_index=1).append_record(two_sheet_file, _rec("ALU-01"))

        vm_steel = self._vm(two_sheet_file, 0)
        vm_alu = self._vm(two_sheet_file, 1)

        assert len(vm_steel.records) == 1
        assert vm_steel.records[0].program_number == "STEEL-01"
        assert len(vm_alu.records) == 1
        assert vm_alu.records[0].program_number == "ALU-01"

    def test_vm_auto_creates_aluminium_sheet(self, single_sheet_file):
        """load_table on a single-sheet file with sheet_index=1 must create the sheet."""
        vm_alu = self._vm(single_sheet_file, 1)
        # Should not raise; should load 0 records from the newly created sheet
        assert vm_alu.records == []

    def test_vm_alu_write_does_not_affect_steel_vm(self, two_sheet_file):
        self._vm(two_sheet_file, 0)
        vm_alu = self._vm(two_sheet_file, 1)

        # Write via alu VM recorder mock
        with patch.object(
            vm_alu._recorder, "record_from_paths", return_value=_rec("ALU-01")
        ):
            vm_alu.load_and_append_batch([Path("/nc/ALU-01.NC")])

        # Reload steel VM from file
        vm_steel2 = self._vm(two_sheet_file, 0)
        assert vm_steel2.records == []
