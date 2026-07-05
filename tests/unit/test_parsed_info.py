"""Tests for ProgramInfo, SheetInfo and helper functions in parsed_info.py."""

import pytest

from app.burn_table.models.parsed_info import (
    ProgramInfo,
    _fmt_dim,
    _strip_thickness_suffix,
)


class TestFmtDim:
    def test_integer_float_strips_decimal(self):
        assert _fmt_dim(5.0) == "5"
        assert _fmt_dim(1700.0) == "1700"

    def test_fractional_float_preserved(self):
        assert _fmt_dim(4.5) == "4.5"
        assert _fmt_dim(1.25) == "1.25"

    def test_zero(self):
        assert _fmt_dim(0.0) == "0"


class TestStripThicknessSuffix:
    def test_removes_dash_decimal(self):
        assert _strip_thickness_suffix("3.3535-4.0", 4.0) == "3.3535"

    def test_removes_dash_integer(self):
        assert _strip_thickness_suffix("1.4301BRUS-8", 8.0) == "1.4301BRUS"

    def test_removes_concatenated_decimal(self):
        assert _strip_thickness_suffix("3.35354.0", 4.0) == "3.3535"

    def test_leaves_grade_number_intact(self):
        # '1.4016MAGNET2' — the '2' is part of the name, not thickness
        assert _strip_thickness_suffix("1.4016MAGNET2", 2.0) == "1.4016MAGNET2"

    def test_no_match_returns_unchanged(self):
        assert _strip_thickness_suffix("1.0037", 5.0) == "1.0037"

    def test_special_suffix_with_text(self):
        assert _strip_thickness_suffix("3.3535SPECIAL5.0", 5.0) == "3.3535SPECIAL"


class TestProgramInfoSheetFormat:
    def test_full_dimensions(self):
        info = ProgramInfo(
            material_code="1.0037",
            thickness=5.0,
            width=1700.0,
            height=1500.0,
        )
        assert info.sheet_format == "1.0037-5X1700X1500"

    def test_fractional_thickness(self):
        info = ProgramInfo(
            material_code="1.4301",
            thickness=1.5,
            width=3000.0,
            height=1500.0,
        )
        assert info.sheet_format == "1.4301-1.5X3000X1500"

    def test_empty_material_gives_empty_string(self):
        info = ProgramInfo(material_code="", thickness=5.0, width=1700.0, height=1500.0)
        assert info.sheet_format == ""

    def test_no_dimensions_gives_just_material(self):
        info = ProgramInfo(material_code="1.0037")
        assert info.sheet_format == "1.0037"

    def test_strips_thickness_from_material_code(self):
        # material_code includes thickness suffix → strip it before building format
        info = ProgramInfo(
            material_code="3.3535-4.0",
            thickness=4.0,
            width=2000.0,
            height=1000.0,
        )
        assert info.sheet_format == "3.3535-4X2000X1000"


class TestProgramInfoDateCz:
    def test_nc_czech_format(self):
        info = ProgramInfo(date_raw="Y2026M 6D30")
        assert info.date_cz == "30.06.2026"

    def test_nc_single_digit_day_padded(self):
        info = ProgramInfo(date_raw="Y2026M 7D 1")
        assert info.date_cz == "01.07.2026"

    def test_yyyymmdd_format(self):
        info = ProgramInfo(date_raw="20261231")
        assert info.date_cz == "31.12.2026"

    def test_unknown_format_returned_as_is(self):
        info = ProgramInfo(date_raw="unknown")
        assert info.date_cz == "unknown"

    def test_empty_date_returns_empty(self):
        info = ProgramInfo(date_raw="")
        assert info.date_cz == ""


class TestProgramInfoTime:
    @pytest.mark.parametrize("raw,expected", [
        ("H21M51S", "00:21:51"),
        ("H 7M28S", "00:07:28"),
        ("H M48S",  "00:00:48"),
        ("1H5M30S", "01:05:30"),
    ])
    def test_formatted_time(self, raw, expected):
        info = ProgramInfo(program_time_raw=raw)
        assert info.program_time_formatted == expected

    @pytest.mark.parametrize("raw,expected", [
        ("H21M51S", "22"),   # 21 min + round-up 51 s → 22
        ("H M48S",  "1"),    # 0 min + round-up 48 s → 1
        ("1H5M30S", "66"),   # 60 + 5 + round-up 30 s → 66
        ("H21M29S", "21"),   # 21 min + 29 s (not round-up) → 21
        ("H M0S",   "0"),    # exactly 0 minutes 0 seconds
    ])
    def test_minutes(self, raw, expected):
        info = ProgramInfo(program_time_raw=raw)
        assert info.program_time_minutes == expected

    def test_unparseable_time_returns_raw(self):
        info = ProgramInfo(program_time_raw="INVALID")
        assert info.program_time_formatted == "INVALID"
        assert info.program_time_minutes == ""
