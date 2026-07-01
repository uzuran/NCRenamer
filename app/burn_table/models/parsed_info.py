"""Intermediate data structures produced by NC/SCH file parsers."""

import re
from dataclasses import dataclass, field


def _fmt_dim(v: float) -> str:
    """Format a dimension float without trailing zeros: 5.0→'5', 4.5→'4.5'."""
    return str(int(v)) if v == int(v) else f"{v:g}"


def _strip_thickness_suffix(material: str, thickness: float) -> str:
    """Remove a trailing thickness value from a material code.

    Handles two formats found in the NC material CSV:
      with dash:    '3.3535-4.0'       → '3.3535'
                    '1.4301BRUS-8'     → '1.4301BRUS'
      concatenated: '3.35354.0'        → '3.3535'
                    '3.3535SPECIAL5.0' → '3.3535SPECIAL'

    Bare integers without a dash (e.g. '1.4016MAGNET2') are left unchanged
    to avoid stripping grade numbers that are part of the material name.
    """
    t_dec = f"{thickness:.1f}"   # e.g. "4.0", "1.5"
    t_int = str(int(thickness))  # e.g. "4",   "1"

    # With dash first: '-4.0' then '-4'
    for suffix in (f"-{t_dec}", f"-{t_int}"):
        if material.endswith(suffix):
            return material[:-len(suffix)]

    # Without dash — only decimal form to avoid stripping grade numbers
    if material.endswith(t_dec) and len(material) > len(t_dec):
        return material[:-len(t_dec)]

    return material


@dataclass
class Material:
    """Material properties extracted from the MA/ and WK/ NC fields.

    Attributes:
        code:       Material code, e.g. '1.0037'.
        thickness:  Sheet thickness in mm, e.g. 5.0.
    """

    code: str
    thickness: float = 0.0


@dataclass
class ProgramInfo:
    """All header data extracted from a single NC program file.

    Attributes:
        program_number: Value of the PR/ field, e.g. '6670-18'.
        material_code:  Value of the MA/ field, e.g. '1.0037'.
        thickness:      Sheet thickness in mm (from WK/).
        width:          Sheet width  in mm (from WK/).
        height:         Sheet height in mm (from WK/).
        program_time_raw: Raw TT/ value, e.g. 'H21M51S'.
        date_raw:       Raw CR/ value in YYYYMMDD format, e.g. '20260630'.
    """

    program_number: str = ""
    material_code: str = ""
    thickness: float = 0.0
    width: float = 0.0
    height: float = 0.0
    program_time_raw: str = ""
    date_raw: str = ""

    # ── derived helpers ─────────────────────────────────────────────────

    @property
    def sheet_format(self) -> str:
        """Format the sheet dimensions as used in column D.

        Example output: '1.0037-5X 1700X 1500'
        """
        if not self.material_code:
            return ""
        if not (self.thickness or self.width or self.height):
            return self.material_code
        base = _strip_thickness_suffix(self.material_code, self.thickness)
        t = _fmt_dim(self.thickness)
        w = _fmt_dim(self.width)
        h = _fmt_dim(self.height)
        return f"{base}-{t}X {w}X {h}"

    @property
    def date_cz(self) -> str:
        """Format NC date as DD.MM.YYYY.

        Handles NC Czech format 'Y2026M 6D30' and raw YYYYMMDD.
        """
        m = re.match(r"Y(\d{4})M\s*(\d+)D(\d+)", self.date_raw)
        if m:
            year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return f"{day:02d}.{month:02d}.{year}"
        if len(self.date_raw) == 8 and self.date_raw.isdigit():
            year = int(self.date_raw[:4])
            month = int(self.date_raw[4:6])
            day = int(self.date_raw[6:])
            return f"{day:02d}.{month:02d}.{year}"
        return self.date_raw

    @property
    def program_time_formatted(self) -> str:
        """Format TT/ time code as HH:MM:SS.

        'H21M51S'  → '00:21:51'
        'H 7M28S'  → '00:07:28'
        'H M48S'   → '00:00:48'  (zero minutes, 48 seconds)
        '1H5M30S'  → '01:05:30'
        """
        m = re.match(r"(\d*)H\s*(\d*)M\s*(\d+)S", self.program_time_raw)
        if not m:
            return self.program_time_raw
        hours = int(m.group(1)) if m.group(1) else 0
        minutes = int(m.group(2)) if m.group(2) else 0
        seconds = int(m.group(3))
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def program_time_minutes(self) -> str:
        """Extract total minutes from raw time code as a string.

        'H21M51S' → '22'  (0 h × 60 + 21 m + round-up seconds)
        'H M48S'  → '1'
        '1H5M30S' → '66'
        """
        m = re.match(r"(\d*)H\s*(\d*)M\s*(\d+)S", self.program_time_raw)
        if not m:
            return ""
        hours = int(m.group(1)) if m.group(1) else 0
        minutes = int(m.group(2)) if m.group(2) else 0
        seconds = int(m.group(3))
        total = hours * 60 + minutes + (1 if seconds >= 30 else 0)
        return str(total)


@dataclass
class SheetInfo:
    """Data extracted from the SCH (schedule / nesting) XML file.

    Attributes:
        product_quantity: Total number of parts to be cut.
        parts_name:       Program / part name (e.g. '6670-18').
    """

    product_quantity: int = 1
    parts_name: str = ""
    raw_fields: dict = field(default_factory=dict)
