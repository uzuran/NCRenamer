"""Comprehensive material-parsing tests for the burn-table import pipeline.

Verifies end-to-end correctness for every material variant in the production list:

  Standard:  1.0026-1.0  1.0330-0.5  1.0037-4.0  1.4301-3.0  2.0070-5.0  3.3535-6.0
  Special:   SPECIAL-3.0  1.4016MAGNET3  3.3535LISTKOVY-5.0  1.0037S235JRG2-4.0
             3.3535ALUNOX  1.0037POZINK-2.0  1.0037HB-8.0  1.0037TRANSPORTKONZOLE
             1.4301BRUS-3.0  1.4301DEROVANY  3.3535SPECIAL5.0

Each test covers the four stages:
  (a) NC text parsing  — PerformanceRecorder.parse_nc()  → material_code
  (b) sheet_format     — ProgramInfo.sheet_format property (ViewModel-stored value)
  (c) TreeView value   — BurnRecord.to_row()[2]  (column C in the 8-col layout)
  (d) Excel round-trip — rewrite_all_records() then read_all_with_separators()

Space-normalisation tests verify that NC files pre-processed by FormatterModel
(which inserts a space between the numeric base and the text suffix) are handled
identically to NC files without the space.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.parsed_info import ProgramInfo, _strip_thickness_suffix
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder


# ── helpers ─────────────────────────────────────────────────────────────────


def _nc(material: str, thickness: float, width: float = 2000.0, height: float = 1000.0) -> str:
    """Build a minimal NC header string with the given material and dimensions."""
    t_str = f"{thickness:.2f}"
    w_str = f"{width:.2f}"
    h_str = f"{height:.2f}"
    return (
        f"(MC/MACHINE)\n"
        f"(PR/6670-18)\n"
        f"(MA/{material})\n"
        f"(WK/    {t_str}T {w_str}X {h_str})\n"
        f"(TT/  H21M51S)\n"
        f"(CR/Y2026M 6D30)\n"
    )


_RECORDER = PerformanceRecorder()


# ══════════════════════════════════════════════════════════════════════════════
# (a) + (b) NC parsing and sheet_format — parametrised over every material
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "ma_field, thickness, expected_code, expected_format",
    [
        # expected_code = raw MA/ value as stored in ProgramInfo.material_code
        #                 (whitespace collapsed, thickness suffix NOT stripped —
        #                 stripping happens only inside sheet_format)
        # ── Standard materials (thickness encoded in MA field with dash) ───────
        ("1.0026-1.0",  1.0,  "1.0026-1.0",          "1.0026-1X2000X1000"),
        ("1.0330-0.5",  0.5,  "1.0330-0.5",          "1.0330-0.5X2000X1000"),
        ("1.0037-4.0",  4.0,  "1.0037-4.0",          "1.0037-4X2000X1000"),
        ("1.4301-3.0",  3.0,  "1.4301-3.0",          "1.4301-3X2000X1000"),
        ("2.0070-5.0",  5.0,  "2.0070-5.0",          "2.0070-5X2000X1000"),
        ("3.3535-6.0",  6.0,  "3.3535-6.0",          "3.3535-6X2000X1000"),
        # ── Standard material — thickness only in WK/ (no suffix in MA) ────────
        ("1.0037",      5.0,  "1.0037",              "1.0037-5X2000X1000"),
        # ── Special: SPECIAL-3.0 ────────────────────────────────────────────────
        ("SPECIAL-3.0", 3.0,  "SPECIAL-3.0",         "SPECIAL-3X2000X1000"),
        # ── Special: grade number (3) is part of the name, NOT the thickness ───
        ("1.4016MAGNET3", 3.0, "1.4016MAGNET3",      "1.4016MAGNET3-3X2000X1000"),
        # ── Special: text suffix + dash-encoded thickness ────────────────────────
        ("3.3535LISTKOVY-5.0",    5.0, "3.3535LISTKOVY-5.0",    "3.3535LISTKOVY-5X2000X1000"),
        ("1.0037S235JRG2-4.0",   4.0, "1.0037S235JRG2-4.0",   "1.0037S235JRG2-4X2000X1000"),
        ("1.0037POZINK-2.0",     2.0, "1.0037POZINK-2.0",     "1.0037POZINK-2X2000X1000"),
        ("1.0037HB-8.0",         8.0, "1.0037HB-8.0",         "1.0037HB-8X2000X1000"),
        ("1.4301BRUS-3.0",       3.0, "1.4301BRUS-3.0",       "1.4301BRUS-3X2000X1000"),
        # ── Special: text suffix, no dash, concatenated decimal thickness ────────
        ("3.3535SPECIAL5.0",     5.0, "3.3535SPECIAL5.0",     "3.3535SPECIAL-5X2000X1000"),
        # ── Special: text suffix only, thickness comes from WK/ ─────────────────
        ("3.3535ALUNOX",         5.0, "3.3535ALUNOX",         "3.3535ALUNOX-5X2000X1000"),
        ("1.4301DEROVANY",       4.0, "1.4301DEROVANY",       "1.4301DEROVANY-4X2000X1000"),
        # (1.0037TRANSPORTKONZOLE tested separately — requires all-zero WK/ line)
    ],
)
class TestMaterialParsingEndToEnd:
    def test_a_nc_parse_captures_material_code(self, ma_field, thickness, expected_code, expected_format):
        """(a) PerformanceRecorder.parse_nc() captures the full material code."""
        nc = _nc(ma_field, thickness)
        info = _RECORDER.parse_nc(nc)
        assert info.material_code == expected_code

    def test_b_program_info_sheet_format(self, ma_field, thickness, expected_code, expected_format):
        """(b) ProgramInfo.sheet_format builds the correct string (ViewModel value)."""
        nc = _nc(ma_field, thickness)
        info = _RECORDER.parse_nc(nc)
        assert info.sheet_format == expected_format

    def test_c_burn_record_treeview_value(self, ma_field, thickness, expected_code, expected_format):
        """(c) BurnRecord.to_row()[2] is the sheet_format shown in the TreeView."""
        rec = BurnRecord(sheet_format=expected_format)
        row = rec.to_row()
        assert row[2] == expected_format


# ── TRANSPORTKONZOLE — no sheet data; WK/ is all-zero ───────────────────────
# Requires a dedicated NC text because _nc() always sets width/height=2000/1000.

_NC_TRANSPORTKONZOLE = (
    "(MC/MACHINE)\n"
    "(PR/6670-18)\n"
    "(MA/1.0037TRANSPORTKONZOLE)\n"
    "(WK/    0.00T 0.00X 0.00)\n"
    "(TT/  H21M51S)\n"
    "(CR/Y2026M 6D30)\n"
)


def test_transportkonzole_material_code():
    info = _RECORDER.parse_nc(_NC_TRANSPORTKONZOLE)
    assert info.material_code == "1.0037TRANSPORTKONZOLE"


def test_transportkonzole_sheet_format_is_just_code():
    """When all WK/ dimensions are zero, sheet_format returns only the code."""
    info = _RECORDER.parse_nc(_NC_TRANSPORTKONZOLE)
    assert info.sheet_format == "1.0037TRANSPORTKONZOLE"


def test_transportkonzole_treeview_value():
    rec = BurnRecord(sheet_format="1.0037TRANSPORTKONZOLE")
    assert rec.to_row()[2] == "1.0037TRANSPORTKONZOLE"


# ══════════════════════════════════════════════════════════════════════════════
# Space-normalisation — FormatterModel inserts a space; parser must collapse it
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "ma_with_space, ma_without_space, thickness",
    [
        # FormatterModel converts (MA/1.0037S235JRG2) → (MA/1.0037 S235JRG2)
        ("1.0037 S235JRG2",   "1.0037S235JRG2",   4.0),
        ("1.4301 BRUS",       "1.4301BRUS",        3.0),
        ("3.3535 LISTKOVY",   "3.3535LISTKOVY",    5.0),
        ("1.0037 POZINK",     "1.0037POZINK",      2.0),
        ("1.0037 HB",         "1.0037HB",          8.0),
        ("3.3535 ALUNOX",     "3.3535ALUNOX",      5.0),
        ("1.4016 MAGNET3",    "1.4016MAGNET3",     3.0),
        ("1.4301 DEROVANY",   "1.4301DEROVANY",    4.0),
    ],
)
class TestSpaceNormalisation:
    def test_space_variant_produces_same_material_code_as_no_space(
        self, ma_with_space, ma_without_space, thickness
    ):
        """NC files processed by FormatterModel (space inserted) must give the same
        material_code as the original unprocessed NC file."""
        nc_space = _nc(ma_with_space, thickness)
        nc_nospace = _nc(ma_without_space, thickness)
        info_space = _RECORDER.parse_nc(nc_space)
        info_nospace = _RECORDER.parse_nc(nc_nospace)
        assert info_space.material_code == info_nospace.material_code

    def test_space_variant_produces_same_sheet_format(
        self, ma_with_space, ma_without_space, thickness
    ):
        """sheet_format must be identical regardless of whether the NC file was
        pre-processed by FormatterModel."""
        nc_space = _nc(ma_with_space, thickness)
        nc_nospace = _nc(ma_without_space, thickness)
        info_space = _RECORDER.parse_nc(nc_space)
        info_nospace = _RECORDER.parse_nc(nc_nospace)
        assert info_space.sheet_format == info_nospace.sheet_format

    def test_space_variant_does_not_truncate_suffix(
        self, ma_with_space, ma_without_space, thickness
    ):
        """The text suffix (BRUS, S235JRG2, …) must appear in the captured material_code
        even when the NC line has a space between the numeric base and the suffix."""
        nc = _nc(ma_with_space, thickness)
        info = _RECORDER.parse_nc(nc)
        assert info.material_code == ma_without_space, (
            f"Expected '{ma_without_space}' but got '{info.material_code}' — "
            "suffix was truncated (space-truncation bug)"
        )


# ══════════════════════════════════════════════════════════════════════════════
# (d) Excel round-trip — sheet_format survives write + read unchanged
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "sheet_format",
    [
        "1.0026-1X2000X1000",
        "1.0330-0.5X2000X1000",
        "1.0037-4X2000X1000",
        "1.4301-3X2000X1000",
        "2.0070-5X2000X1000",
        "3.3535-6X2000X1000",
        "SPECIAL-3X2000X1000",
        "1.4016MAGNET3-3X2000X1000",
        "3.3535LISTKOVY-5X2000X1000",
        "1.0037S235JRG2-4X2000X1000",
        "3.3535ALUNOX-5X2000X1000",
        "1.0037POZINK-2X2000X1000",
        "1.0037HB-8X2000X1000",
        "1.0037TRANSPORTKONZOLE",
        "1.4301BRUS-3X2000X1000",
        "1.4301DEROVANY-4X2000X1000",
        "3.3535SPECIAL-5X2000X1000",
    ],
)
class TestExcelRoundTrip:
    """(d) sheet_format must survive a full write → read cycle in both .xls and .xlsx."""

    @pytest.fixture(params=["table.xls", "table.xlsx"])
    def table_file(self, request, tmp_path) -> Path:
        from app.burn_table.services.table_factory import TableFactory
        path: Path = tmp_path / str(request.param)
        TableFactory().create(path)
        return path

    def test_sheet_format_survives_excel_round_trip(self, table_file, sheet_format):
        from app.burn_table.services.excel_reader import ExcelReader
        from app.burn_table.services.excel_writer import ExcelWriter

        rec = BurnRecord(
            date="14.07.2026",
            program_number="6670-18",
            sheet_format=sheet_format,
            sheet_count=1,
            total_time="00:21:51",
        )
        writer = ExcelWriter()
        reader = ExcelReader()
        writer.rewrite_all_records(table_file, [rec])
        result = reader.read_all(table_file)
        assert len(result) == 1
        assert result[0].sheet_format == sheet_format, (
            f"sheet_format corrupted: wrote '{sheet_format}' but read back '{result[0].sheet_format}'"
        )


# ══════════════════════════════════════════════════════════════════════════════
# _strip_thickness_suffix — exhaustive coverage of all material shapes
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "material, thickness, expected",
    [
        # Standard with dash-decimal suffix
        ("1.0026-1.0",           1.0,  "1.0026"),
        ("1.0330-0.5",           0.5,  "1.0330"),
        ("1.0037-4.0",           4.0,  "1.0037"),
        ("1.4301-3.0",           3.0,  "1.4301"),
        ("2.0070-5.0",           5.0,  "2.0070"),
        ("3.3535-6.0",           6.0,  "3.3535"),
        # Standard with dash-integer suffix (no decimal point)
        ("1.4301BRUS-8",         8.0,  "1.4301BRUS"),
        ("1.4301BRUS-3",         3.0,  "1.4301BRUS"),
        # Standard with concatenated decimal (no dash)
        ("3.35354.0",            4.0,  "3.3535"),
        ("3.3535SPECIAL5.0",     5.0,  "3.3535SPECIAL"),
        # Text suffix with dash-decimal thickness
        ("SPECIAL-3.0",          3.0,  "SPECIAL"),
        ("3.3535LISTKOVY-5.0",   5.0,  "3.3535LISTKOVY"),
        ("1.0037S235JRG2-4.0",  4.0,  "1.0037S235JRG2"),
        ("1.0037POZINK-2.0",     2.0,  "1.0037POZINK"),
        ("1.0037HB-8.0",         8.0,  "1.0037HB"),
        ("1.4301BRUS-3.0",       3.0,  "1.4301BRUS"),
        # Grade number that must NOT be stripped (no dash, integer only)
        ("1.4016MAGNET3",        3.0,  "1.4016MAGNET3"),
        # No suffix to strip — returned unchanged
        ("1.0037",               5.0,  "1.0037"),
        ("3.3535ALUNOX",         5.0,  "3.3535ALUNOX"),
        ("1.4301DEROVANY",       4.0,  "1.4301DEROVANY"),
        ("1.0037TRANSPORTKONZOLE", 4.0, "1.0037TRANSPORTKONZOLE"),
        ("1.0037S235JRG2",       4.0,  "1.0037S235JRG2"),
    ],
)
def test_strip_thickness_suffix(material, thickness, expected):
    assert _strip_thickness_suffix(material, thickness) == expected
