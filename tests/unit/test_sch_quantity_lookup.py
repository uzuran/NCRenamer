"""Tests for SCH-file quantity lookup and SCH file discovery."""

from pathlib import Path
from unittest.mock import patch

from app.burn_table.models.parsed_info import ProgramInfo, SheetInfo
from app.burn_table.services.xml_parser import XmlParser
from app.burn_table.viewmodels.burn_view_model import BurnViewModel
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder

# A multi-program SCH file — one sheet was used to cut four different programs
_MULTI_BLOCK_SCH = """\
<?xml version="1.0" encoding="utf-8"?>
<schedule_info MachineName="ENSIS3015AJ">
  <parts_info>
    <parts_name>6684-97</parts_name>
    <product_quantity>1</product_quantity>
  </parts_info>
  <parts_info>
    <parts_name>6684-04</parts_name>
    <product_quantity>2</product_quantity>
  </parts_info>
  <parts_info>
    <parts_name>6684-16</parts_name>
    <product_quantity>4</product_quantity>
  </parts_info>
  <parts_info>
    <parts_name>6684-99</parts_name>
    <product_quantity>3</product_quantity>
  </parts_info>
</schedule_info>
"""


class TestXmlParserFindQuantityForProgram:
    def setup_method(self):
        self.parser = XmlParser()

    def test_finds_quantity_for_first_program(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "6684-97") == 1

    def test_finds_quantity_for_middle_program(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "6684-04") == 2

    def test_finds_quantity_for_last_program(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "6684-99") == 3

    def test_finds_quantity_greater_than_one(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "6684-16") == 4

    def test_returns_1_when_program_not_found(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "9999-00") == 1

    def test_returns_1_for_empty_program_number(self):
        assert self.parser.find_quantity_for_program(_MULTI_BLOCK_SCH, "") == 1

    def test_returns_1_for_invalid_xml(self):
        assert self.parser.find_quantity_for_program("not xml", "6684-97") == 1


class TestFindSchForNc:
    """Tests for BurnViewModel.find_sch_for_nc() filesystem lookup."""

    def test_exact_stem_match(self, tmp_path):
        sch = tmp_path / "6670-18.SCH"
        sch.write_text("")
        nc = tmp_path / "6670-18.NC"
        assert BurnViewModel.find_sch_for_nc(nc) == sch

    def test_exact_match_case_insensitive_extension(self, tmp_path):
        sch = tmp_path / "6670-18.sch"
        sch.write_text("")
        nc = tmp_path / "6670-18.NC"
        assert BurnViewModel.find_sch_for_nc(nc) == sch

    def test_job_prefix_fallback(self, tmp_path):
        # 6684-97.NC has no 6684-97.SCH; falls back to 6684-32.SCH
        sch = tmp_path / "6684-32.SCH"
        sch.write_text("")
        nc = tmp_path / "6684-97.NC"
        assert BurnViewModel.find_sch_for_nc(nc) == sch

    def test_exact_match_preferred_over_prefix(self, tmp_path):
        exact = tmp_path / "6684-97.SCH"
        exact.write_text("")
        other = tmp_path / "6684-32.SCH"
        other.write_text("")
        nc = tmp_path / "6684-97.NC"
        assert BurnViewModel.find_sch_for_nc(nc) == exact

    def test_returns_none_when_no_sch_exists(self, tmp_path):
        nc = tmp_path / "6684-97.NC"
        assert BurnViewModel.find_sch_for_nc(nc) is None

    def test_returns_none_for_nc_without_dash(self, tmp_path):
        # No dash in stem → no prefix fallback, no exact match → None
        nc = tmp_path / "PROGRAM.NC"
        assert BurnViewModel.find_sch_for_nc(nc) is None


class TestPerformanceRecorderTargetedQuantity:
    """Integration: record_from_paths() picks quantity for the correct NC program."""

    def setup_method(self):
        self.recorder = PerformanceRecorder()

    def _nc_text(self, program_number: str) -> str:
        return (
            f"(PR/{program_number})\n"
            "(MA/1.0037)\n"
            "(WK/    5.00T 1700.00X 1500.00)\n"
            "(TT/  H21M51S)\n"
            "(CR/Y2026M 6D30)\n"
        )

    def test_picks_correct_quantity_for_program_97(self):
        nc_path = Path("/fake/6684-97.NC")
        with (
            patch.object(self.recorder._file_service, "read_nc", return_value=self._nc_text("6684-97")),
            patch.object(self.recorder._file_service, "read_sch", return_value=_MULTI_BLOCK_SCH),
        ):
            record = self.recorder.record_from_paths(nc_path, sch_path=Path("/fake/6684-32.SCH"))

        assert record.sheet_count == 1
        assert record.program_number == "6684-97"

    def test_picks_correct_quantity_for_program_04(self):
        nc_path = Path("/fake/6684-04.NC")
        with (
            patch.object(self.recorder._file_service, "read_nc", return_value=self._nc_text("6684-04")),
            patch.object(self.recorder._file_service, "read_sch", return_value=_MULTI_BLOCK_SCH),
        ):
            record = self.recorder.record_from_paths(nc_path, sch_path=Path("/fake/6684-32.SCH"))

        assert record.sheet_count == 2
        assert record.program_number == "6684-04"

    def test_picks_correct_quantity_for_program_16(self):
        nc_path = Path("/fake/6684-16.NC")
        with (
            patch.object(self.recorder._file_service, "read_nc", return_value=self._nc_text("6684-16")),
            patch.object(self.recorder._file_service, "read_sch", return_value=_MULTI_BLOCK_SCH),
        ):
            record = self.recorder.record_from_paths(nc_path, sch_path=Path("/fake/6684-32.SCH"))

        assert record.sheet_count == 4

    def test_defaults_to_1_when_program_not_in_sch(self):
        nc_path = Path("/fake/6684-55.NC")
        with (
            patch.object(self.recorder._file_service, "read_nc", return_value=self._nc_text("6684-55")),
            patch.object(self.recorder._file_service, "read_sch", return_value=_MULTI_BLOCK_SCH),
        ):
            record = self.recorder.record_from_paths(nc_path, sch_path=Path("/fake/6684-32.SCH"))

        assert record.sheet_count == 1

    def test_program_number_from_nc_stem_when_no_pr_tag(self):
        # NC without (PR/...) — program number must come from filename, not first SCH block
        nc_text = "(MA/1.0037)\n(WK/ 5.00T 1700.00X 1500.00)\n(TT/ H21M51S)\n(CR/Y2026M 6D30)\n"
        nc_path = Path("/fake/6684-04.NC")
        with (
            patch.object(self.recorder._file_service, "read_nc", return_value=nc_text),
            patch.object(self.recorder._file_service, "read_sch", return_value=_MULTI_BLOCK_SCH),
        ):
            record = self.recorder.record_from_paths(nc_path, sch_path=Path("/fake/6684-32.SCH"))

        # stem wins over first SCH block ("6684-97")
        assert record.program_number == "6684-04"
        assert record.sheet_count == 2
