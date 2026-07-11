"""PerformanceRecorder — parses NC and SCH files into a BurnRecord."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

from app.burn_table.models.burn_record import BurnRecord
from app.burn_table.models.parsed_info import ProgramInfo, SheetInfo
from app.burn_table.services.file_service import FileService
from app.burn_table.services.xml_parser import XmlParser


class PerformanceRecorder:
    """Orchestrates NC/SCH file parsing and assembles a BurnRecord.

    This is a ViewModel-level component: it coordinates services,
    applies business rules (date formatting, sheet-format string
    construction), and returns a ready-to-append BurnRecord.

    NC parsing recognises header lines in the format:
        (CR/YYYYMMDD)   - creation / burn date
        (PR/xxxxxxx)    - program number
        (MA/x.xxxx)     - material code
        (WK/5.00T1700.00X1500.00) - thickness x width x height
        (TT/H21M51S)    - total cutting time

    Lines with or without parentheses are both supported.
    """

    # Regex patterns for NC header fields (parentheses optional).
    # WK and TT often have leading whitespace after the slash; [^\n\)] is
    # greedy and stops at ) or newline — the caller strips the result.
    # CR date may be YYYYMMDD or already in Czech format (Y2026M 6D30).
    _NC_PATTERNS: ClassVar[dict[str, str]] = {
        "date": r"\(?CR/([^\n\)]+)\)?",
        "program": r"\(?PR/([^\s\n\)]+)\)?",
        "material": r"\(?MA/([^\s\n\)]+)\)?",
        "workpiece": r"\(?WK/([^\n\)]+)\)?",
        "time": r"\(?TT/([^\n\)]+)\)?",
    }

    # Two possible WK sub-formats (spaces between values are allowed):
    #   T5.00X1700.00Y1500.00   (T prefix)
    #   5.00T 1700.00X 1500.00  (number-first, may have spaces)
    _WK_T_FIRST = re.compile(r"T([\d.]+)X([\d.]+)Y([\d.]+)")
    _WK_NUM_FIRST = re.compile(r"([\d.]+)T\s*([\d.]+)X\s*([\d.]+)")

    def __init__(
        self,
        file_service: FileService | None = None,
        xml_parser: XmlParser | None = None,
    ) -> None:
        self._file_service = file_service or FileService()
        self._xml_parser = xml_parser or XmlParser()

    # ── public API ───────────────────────────────────────────────────────

    def record_from_paths(
        self,
        nc_path: Path,
        sch_path: Path | None = None,
        product_group: str = "",
        operator: str = "",
    ) -> BurnRecord:
        """Parse *nc_path* (and optionally *sch_path*) into a BurnRecord.

        Args:
            nc_path:       Path to the .NC program file.
            sch_path:      Optional path to the .SCH / .XML schedule file.
            product_group: Product type to populate column I.

        Returns:
            A populated BurnRecord ready to be appended to the table.

        Raises:
            FileNotFoundError: if *nc_path* does not exist.
            ValueError:        if the NC file cannot be parsed.
        """
        nc_text = self._file_service.read_nc(nc_path)
        program_info = self.parse_nc(nc_text)

        sheet_info = SheetInfo(product_quantity=1)
        if sch_path is not None:
            sch_text = self._file_service.read_sch(sch_path)
            try:
                # parse() gives us parts_name (used as program-number fallback)
                sheet_info = self._xml_parser.parse(sch_text)
                # Override quantity with the entry that matches *this* NC program.
                # The SCH often contains one block per program cut on the same sheet,
                # so a generic sum would give wrong results.
                program_number = program_info.program_number or (
                    nc_path.stem if nc_path else ""
                )
                targeted_qty = self._xml_parser.find_quantity_for_program(
                    sch_text, program_number
                )
                sheet_info = SheetInfo(
                    product_quantity=targeted_qty,
                    parts_name=sheet_info.parts_name,
                    raw_fields=sheet_info.raw_fields,
                )
            except ValueError:
                pass  # SCH parse failure is non-fatal; use default quantity

        return self._build_record(
            program_info, sheet_info, product_group, nc_path, operator
        )

    def parse_nc(self, nc_text: str) -> ProgramInfo:
        """Extract header fields from the raw NC program text.

        Only the first 50 lines are scanned (header is always at the top).
        """
        header = "\n".join(nc_text.splitlines()[:50])

        def _find(key: str) -> str:
            m = re.search(self._NC_PATTERNS[key], header, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        date_raw = _find("date")
        program_number = _find("program")
        material_code = _find("material")
        wk_raw = _find("workpiece")
        time_raw = _find("time")

        thickness, width, height = self._parse_wk(wk_raw)

        return ProgramInfo(
            program_number=program_number,
            material_code=material_code,
            thickness=thickness,
            width=width,
            height=height,
            program_time_raw=time_raw,
            date_raw=date_raw,
        )

    # ── private helpers ──────────────────────────────────────────────────

    def _parse_wk(self, wk_raw: str) -> tuple[float, float, float]:
        """Return (thickness, width, height) from a raw WK/ value.

        Handles both 'T5.00X1700.00Y1500.00' and '5.00T1700.00X1500.00'.
        Returns (0.0, 0.0, 0.0) if the value cannot be parsed.
        """
        if not wk_raw:
            return (0.0, 0.0, 0.0)

        m = self._WK_T_FIRST.search(wk_raw)
        if m:
            return (float(m.group(1)), float(m.group(2)), float(m.group(3)))

        m = self._WK_NUM_FIRST.search(wk_raw)
        if m:
            return (float(m.group(1)), float(m.group(2)), float(m.group(3)))

        return (0.0, 0.0, 0.0)

    @staticmethod
    def _multiply_time(time_str: str, count: int) -> str:
        """Multiply a HH:MM:SS time string by *count* and return HH:MM:SS.

        Example: _multiply_time("00:03:09", 3) -> "00:09:27"

        Falls back to *time_str* unchanged when *count* ≤ 1 or the format
        cannot be parsed.
        """
        if not time_str or count <= 1:
            return time_str
        m = re.match(r"(\d+):(\d+):(\d+)$", time_str)
        if not m:
            return time_str
        base = timedelta(
            hours=int(m.group(1)),
            minutes=int(m.group(2)),
            seconds=int(m.group(3)),
        )
        total_s = int((base * count).total_seconds())
        hh, rem = divmod(total_s, 3600)
        mm, ss = divmod(rem, 60)
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    @staticmethod
    def _build_record(
        info: ProgramInfo,
        sheet: SheetInfo,
        product_group: str,
        nc_path: Path | None = None,
        operator: str = "",
    ) -> BurnRecord:
        """Assemble a BurnRecord from parsed data.

        Program number priority:
            1. (PR/…) tag inside the NC file
            2. <parts_name> from the SCH/XML file
            3. NC filename stem  (e.g. '6670-18' from '6670-18.NC')
        """
        # Priority: (PR/…) tag > NC filename stem > first <parts_name> in SCH.
        # NC stem beats SCH parts_name because a multi-block SCH file returns
        # the first block's name regardless of which NC we're processing.
        program_number = (
            info.program_number or (nc_path.stem if nc_path else "") or sheet.parts_name
        )
        count = max(1, sheet.product_quantity)
        return BurnRecord(
            date=info.date_cz,
            program_number=program_number,
            note="",
            sheet_format=info.sheet_format,
            sheet_count=sheet.product_quantity,
            program_time=info.program_time_minutes,
            total_time=PerformanceRecorder._multiply_time(
                info.program_time_formatted, count
            ),
            burned="",
            product_group=product_group,
            operator=operator,
        )
