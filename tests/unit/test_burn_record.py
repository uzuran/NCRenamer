"""Tests for BurnRecord model - to_row(), from_row(), is_empty()."""

from app.burn_table.models.burn_record import BurnRecord


class TestToRow:
    def test_returns_nine_elements(self):
        rec = BurnRecord()
        assert len(rec.to_row()) == 9

    def test_correct_column_order(self):
        rec = BurnRecord(
            date="30.06.2026",
            program_number="6670-18",
            note="test",
            sheet_format="1.0037-5X1700X1500",
            sheet_count=3,
            total_time="00:21:51",
            burned="ano",
            product_group="pwa",
            operator="Jan",
        )
        row = rec.to_row()
        assert row[0] == "30.06.2026"
        assert row[1] == "6670-18"
        assert row[2] == "test"
        assert row[3] == "1.0037-5X1700X1500"
        assert row[4] == 3
        assert row[5] == "00:21:51"
        assert row[6] == "ano"
        assert row[7] == "pwa"
        assert row[8] == "Jan"

    def test_zero_sheet_count_becomes_empty_string(self):
        rec = BurnRecord(sheet_count=0)
        assert rec.to_row()[4] == ""

    def test_nonzero_sheet_count_is_integer(self):
        rec = BurnRecord(sheet_count=5)
        assert rec.to_row()[4] == 5


class TestFromRow9Col:
    def _row(self):
        return [
            "30.06.2026",
            "6670-18",
            "note",
            "1.0037-5X1700X1500",
            3,
            "00:21:51",
            "ano",
            "pwa",
            "Jan",
        ]

    def test_all_fields_populated(self):
        rec = BurnRecord.from_row(self._row())
        assert rec.date == "30.06.2026"
        assert rec.program_number == "6670-18"
        assert rec.note == "note"
        assert rec.sheet_format == "1.0037-5X1700X1500"
        assert rec.sheet_count == 3
        assert rec.total_time == "00:21:51"
        assert rec.burned == "ano"
        assert rec.product_group == "pwa"
        assert rec.operator == "Jan"

    def test_none_values_become_empty_strings(self):
        row = [None] * 9
        rec = BurnRecord.from_row(row)
        assert rec.date == ""
        assert rec.program_number == ""
        assert rec.sheet_count == 0

    def test_float_sheet_count_truncated(self):
        row = self._row()
        row[4] = 2.0  # Excel often returns floats
        rec = BurnRecord.from_row(row)
        assert rec.sheet_count == 2

    def test_invalid_sheet_count_becomes_zero(self):
        row = self._row()
        row[4] = "abc"
        rec = BurnRecord.from_row(row)
        assert rec.sheet_count == 0

    def test_strips_whitespace_from_strings(self):
        row = ["  30.06.2026  ", "  6670-18  "] + [""] * 7
        rec = BurnRecord.from_row(row)
        assert rec.date == "30.06.2026"
        assert rec.program_number == "6670-18"

    def test_short_row_pads_missing_columns(self):
        rec = BurnRecord.from_row(["date", "prog"])
        assert rec.date == "date"
        assert rec.program_number == "prog"
        assert rec.note == ""
        assert rec.operator == ""

    def test_empty_row_gives_default_record(self):
        rec = BurnRecord.from_row([])
        assert rec.date == ""
        assert rec.program_number == ""


class TestFromRow10ColLegacy:
    """Legacy 10-column format: col F = program_time, col J = operator."""

    def _legacy_row(self):
        return [
            "30.06.2026",
            "6670-18",
            "note",
            "1.0037-5X1700X1500",
            3,
            "22",  # F = program_time (minutes)
            "00:21:51",
            "ano",
            "pwa",
            "Jan",  # J = operator
        ]

    def test_detects_legacy_by_nonempty_col_j(self):
        rec = BurnRecord.from_row(self._legacy_row())
        assert rec.program_time == "22"
        assert rec.total_time == "00:21:51"
        assert rec.operator == "Jan"

    def test_empty_col_j_treated_as_new_format(self):
        row = self._legacy_row()
        row[9] = ""  # col J empty → new format
        rec = BurnRecord.from_row(row)
        # New format: col F is total_time, col J is ignored
        assert rec.total_time == "22"
        assert rec.operator == "pwa"  # col I in new format

    def test_none_col_j_treated_as_new_format(self):
        row = self._legacy_row()
        row[9] = None
        rec = BurnRecord.from_row(row)
        assert rec.total_time == "22"


class TestIsEmpty:
    def test_fully_empty_record_is_empty(self):
        assert BurnRecord().is_empty() is True

    def test_record_with_date_is_not_empty(self):
        assert BurnRecord(date="30.06.2026").is_empty() is False

    def test_record_with_program_number_is_not_empty(self):
        assert BurnRecord(program_number="6670-18").is_empty() is False

    def test_record_with_sheet_format_is_not_empty(self):
        assert BurnRecord(sheet_format="1.0037-5X1700X1500").is_empty() is False

    def test_record_with_total_time_is_not_empty(self):
        assert BurnRecord(total_time="00:21:51").is_empty() is False

    def test_only_note_does_not_make_non_empty(self):
        # note alone is not a meaningful field
        assert BurnRecord(note="just a note").is_empty() is True

    def test_only_operator_does_not_make_non_empty(self):
        assert BurnRecord(operator="Jan").is_empty() is True
