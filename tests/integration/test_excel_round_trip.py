"""Integration tests: write records to a file and read them back correctly.

Tests cover both .xls and .xlsx, verifying:
- ExcelWriter.append_record writes to the correct row
- ExcelReader.read_all returns the records with correct values
- FreeSlotDetector counts used rows using column B (not column A)
- The 'date once' design (empty date in row 2+) is handled correctly
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.services.excel_reader import ExcelReader
from app.burn_table.services.excel_writer import ExcelWriter
from app.burn_table.services.free_slot_detector import FreeSlotDetector
from app.burn_table.services.table_factory import TableFactory


def _rec(program: str = "6670-18", date: str = "30.06.2026", fmt: str = "1.0037-5X1700X1500") -> BurnRecord:
    return BurnRecord(
        date=date,
        program_number=program,
        note="",
        sheet_format=fmt,
        sheet_count=3,
        total_time="00:21:51",
        burned="",
        product_group="pwa",
        operator="Jan",
    )


@pytest.fixture(params=["table.xls", "table.xlsx"])
def empty_table(request, tmp_path) -> Path:
    """Empty burn table in both formats."""
    path: Path = tmp_path / str(request.param)
    TableFactory().create(path)
    return path


class TestAppendAndRead:
    def test_single_record_round_trip(self, empty_table):
        writer = ExcelWriter()
        reader = ExcelReader()
        rec = _rec()

        writer.append_record(empty_table, rec)
        records = reader.read_all(empty_table)

        assert len(records) == 1
        assert records[0].program_number == "6670-18"
        assert records[0].sheet_format == "1.0037-5X1700X1500"
        assert records[0].sheet_count == 3

    def test_multiple_records_appended_in_order(self, empty_table):
        writer = ExcelWriter()
        reader = ExcelReader()
        programs = ["AAA-01", "BBB-02", "CCC-03"]

        for prog in programs:
            writer.append_record(empty_table, _rec(program=prog))

        records = reader.read_all(empty_table)
        assert [r.program_number for r in records] == programs

    def test_empty_date_rows_are_read_as_used(self, empty_table):
        """Rows with empty date (col A) but non-empty program (col B) must count as used.

        Regression test for the bug where col A was used as the 'occupied' marker.
        """
        writer = ExcelWriter()
        reader = ExcelReader()

        rec_with_date = _rec(program="AAA-01", date="30.06.2026")
        rec_no_date = _rec(program="BBB-02", date="")  # empty date, non-empty program

        writer.append_record(empty_table, rec_with_date)
        writer.append_record(empty_table, rec_no_date)

        records = reader.read_all(empty_table)
        assert len(records) == 2
        assert records[1].program_number == "BBB-02"
        assert records[1].date == ""

    def test_append_returns_correct_row_number(self, empty_table):
        writer = ExcelWriter()
        row_num = writer.append_record(empty_table, _rec())
        assert row_num == 3  # first data row is Excel row 3


class TestFreeSlotDetector:
    def test_empty_table_has_34_free_rows(self, empty_table):
        detector = FreeSlotDetector()
        status = detector.detect(empty_table)
        assert status.free_rows == 34
        assert status.used_rows == 0
        assert status.is_full is False

    def test_one_record_reduces_free_count(self, empty_table):
        ExcelWriter().append_record(empty_table, _rec())
        status = FreeSlotDetector().detect(empty_table)
        assert status.used_rows == 1
        assert status.free_rows == 33

    def test_empty_date_row_still_counted_as_used(self, empty_table):
        """FreeSlotDetector must use col B as marker, not col A."""
        writer = ExcelWriter()
        writer.append_record(empty_table, _rec(date="30.06.2026"))
        writer.append_record(empty_table, _rec(program="BBB", date=""))  # empty date

        status = FreeSlotDetector().detect(empty_table)
        assert status.used_rows == 2

    def test_detect_from_records_matches_detect(self, empty_table):
        for i in range(5):
            ExcelWriter().append_record(empty_table, _rec(program=f"X-{i:02d}"))

        from_file = FreeSlotDetector().detect(empty_table)
        from_count = FreeSlotDetector().detect_from_records(5)

        assert from_file.used_rows == from_count.used_rows
        assert from_file.free_rows == from_count.free_rows

    def test_warning_threshold_at_five_free(self):
        st = FreeSlotDetector().detect_from_records(29)  # 34 - 29 = 5 free
        assert st.warning == "warning"

    def test_critical_threshold_at_two_free(self):
        st = FreeSlotDetector().detect_from_records(32)  # 34 - 32 = 2 free
        assert st.warning == "critical"

    def test_is_full_at_zero_free(self):
        st = FreeSlotDetector().detect_from_records(34)
        assert st.is_full is True
        assert st.free_rows == 0


class TestClearAllRecords:
    def test_clear_removes_data_rows(self, empty_table):
        writer = ExcelWriter()
        reader = ExcelReader()
        for prog in ["A", "B", "C"]:
            writer.append_record(empty_table, _rec(program=prog))

        writer.clear_all_records(empty_table)
        records = reader.read_all(empty_table)
        assert records == []

    def test_clear_resets_free_slot_to_34(self, empty_table):
        ExcelWriter().append_record(empty_table, _rec())
        ExcelWriter().clear_all_records(empty_table)
        status = FreeSlotDetector().detect(empty_table)
        assert status.free_rows == 34

    def test_header_row_preserved_after_clear(self, empty_table):
        ExcelWriter().append_record(empty_table, _rec())
        ExcelWriter().clear_all_records(empty_table)
        # After clear, reading again should return empty (not header row as data)
        records = ExcelReader().read_all(empty_table)
        assert records == []


class TestUpdateHeader:
    def test_update_header_does_not_destroy_data(self, empty_table):
        writer = ExcelWriter()
        reader = ExcelReader()
        writer.append_record(empty_table, _rec())
        writer.update_header(empty_table)  # should not wipe data
        records = reader.read_all(empty_table)
        assert len(records) == 1

    def test_update_header_writes_expected_header_text(self, empty_table):
        """Header row 1 must contain the column labels after update."""
        ExcelWriter().update_header(empty_table)
        if empty_table.suffix == ".xlsx":
            import openpyxl
            ws = openpyxl.load_workbook(empty_table, read_only=True).active
            assert ws.cell(row=1, column=1).value == "Datum pálení"
        else:
            import xlrd
            ws = xlrd.open_workbook(str(empty_table)).sheet_by_index(0)
            assert "Datum" in str(ws.cell_value(0, 0))
