"""Tests that the NC/SCH parsers handle the real-world file formats correctly."""

from app.burn_table.services.xml_parser import XmlParser
from app.burn_table.viewmodels.performance_recorder import PerformanceRecorder

# Exact content from the user's machine (whitespace preserved)
_NC_CONTENT = """\
(MC/ENSIS3015AJ)
(MN/ 244)
(MA/1.0037)
(PZ/  145.50X  132.77)
(WK/    5.00T 1700.00X 1500.00)
(BP/    0.00X    0.00)
(CC/  PF  0.00S\t3300.00P\t200.00Q\t30.00D\t0.00R\t1.20M\t0)
(TT/  H21M51S)
(CR/Y2026M 6D30)
(LC/0)
(LA/0)
(WN/0)
"""

_SCH_CONTENT = """\
<?xml version="1.0" encoding="utf-8"?>
<schedule_info MachineName="ENSIS3015AJ">
  <parts_info>
    <server_name />
    <folder_name />
    <parts_name>6670-18</parts_name>
    <product_quantity>1</product_quantity>
    <reception_quantity>0</reception_quantity>
    <rejection_quantity>0</rejection_quantity>
    <complete_code>2</complete_code>
    <thickness>5</thickness>
    <material_name>1.0037</material_name>
    <punch_number>0</punch_number>
    <die_number>0</die_number>
    <utilization>0</utilization>
  </parts_info>
</schedule_info>
"""


class TestXmlParser:
    def setup_method(self):
        self.parser = XmlParser()

    def test_extracts_product_quantity(self):
        info = self.parser.parse(_SCH_CONTENT)
        assert info.product_quantity == 1

    def test_extracts_parts_name(self):
        info = self.parser.parse(_SCH_CONTENT)
        assert info.parts_name == "6670-18"


class TestPerformanceRecorder:
    def setup_method(self):
        self.recorder = PerformanceRecorder()

    def test_parses_date_czech_format(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.date_raw == "Y2026M 6D30"

    def test_date_cz_returns_dd_mm_yyyy(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.date_cz == "30.06.2026"

    def test_parses_material(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.material_code == "1.0037"

    def test_parses_workpiece_with_leading_spaces(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.thickness == 5.0
        assert info.width == 1700.0
        assert info.height == 1500.0

    def test_sheet_format_string(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.sheet_format == "1.0037-5X 1700X 1500"

    def test_parses_time_with_leading_spaces(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.program_time_raw == "H21M51S"

    def test_program_time_minutes(self):
        info = self.recorder.parse_nc(_NC_CONTENT)
        # H21M51S → 0h + 21m + round-up 51s → 22 minutes
        assert info.program_time_minutes == "22"

    def test_no_pr_tag_program_number_empty_in_nc(self):
        # The NC header has no (PR/...) tag — parse_nc returns empty string
        info = self.recorder.parse_nc(_NC_CONTENT)
        assert info.program_number == ""

    def test_full_record_program_number_from_sch(self):
        xml_parser = XmlParser()
        sheet_info = xml_parser.parse(_SCH_CONTENT)
        nc_info = self.recorder.parse_nc(_NC_CONTENT)
        record = self.recorder._build_record(nc_info, sheet_info, product_group="Ocelové díly")

        assert record.date == "30.06.2026"
        assert record.program_number == "6670-18"  # from SCH parts_name
        assert record.sheet_format == "1.0037-5X 1700X 1500"
        assert record.sheet_count == 1
        assert record.total_time == "00:21:51"
        assert record.program_time == "22"
        assert record.product_group == "Ocelové díly"

    def test_program_number_falls_back_to_nc_filename(self):
        # No SCH → program number comes from the NC filename stem
        from pathlib import Path
        nc_info = self.recorder.parse_nc(_NC_CONTENT)
        sheet_info_empty = __import__(
            "app.burn_table.models.parsed_info", fromlist=["SheetInfo"]
        ).SheetInfo()
        nc_path = Path("/some/folder/6670-18.NC")
        record = self.recorder._build_record(
            nc_info, sheet_info_empty, product_group="", nc_path=nc_path
        )
        assert record.program_number == "6670-18"
