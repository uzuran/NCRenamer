"""BurnRecord — one data row (columns A–J) in the burn table."""

from dataclasses import dataclass, field


@dataclass
class BurnRecord:
    """Represents a single entry in the burn-cutting production table.

    Columns match the fixed Excel layout A–J:
        A – date (Czech format  e.g. 'Y2026M 6D30')
        B – program_number      e.g. '6670-18'
        C – note                free-text comment
        D – sheet_format        e.g. '1.0037 5.00T 1700.00X 1500.00'
        E – sheet_count         number of sheets
        F – program_time        cutting time in minutes (string, may be blank)
        G – total_time          raw time code e.g. 'H21M51S'
        H – burned              completion / burned-off note
        I – product_group       product type and group
        J – operator            name of the operator who ran the job
    """

    date: str = field(default="")
    program_number: str = field(default="")
    note: str = field(default="")
    sheet_format: str = field(default="")
    sheet_count: int = field(default=0)
    program_time: str = field(default="")
    total_time: str = field(default="")
    burned: str = field(default="")
    product_group: str = field(default="")
    operator: str = field(default="")

    def is_empty(self) -> bool:
        """Return True when the record contains no meaningful data."""
        return not any([
            self.date,
            self.program_number,
            self.sheet_format,
            self.total_time,
        ])

    def to_row(self) -> list[str | int]:
        """Return a flat list suitable for writing to a single Excel row."""
        return [
            self.date,
            self.program_number,
            self.note,
            self.sheet_format,
            self.sheet_count if self.sheet_count else "",
            self.program_time,
            self.total_time,
            self.burned,
            self.product_group,
            self.operator,
        ]

    @classmethod
    def from_row(cls, row: list) -> "BurnRecord":
        """Construct a BurnRecord from a flat list of cell values (A–J)."""

        def _str(val: object) -> str:
            return str(val).strip() if val is not None else ""

        def _int(val: object) -> int:
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0

        return cls(
            date=_str(row[0] if len(row) > 0 else None),
            program_number=_str(row[1] if len(row) > 1 else None),
            note=_str(row[2] if len(row) > 2 else None),
            sheet_format=_str(row[3] if len(row) > 3 else None),
            sheet_count=_int(row[4] if len(row) > 4 else None),
            program_time=_str(row[5] if len(row) > 5 else None),
            total_time=_str(row[6] if len(row) > 6 else None),
            burned=_str(row[7] if len(row) > 7 else None),
            product_group=_str(row[8] if len(row) > 8 else None),
            operator=_str(row[9] if len(row) > 9 else None),
        )
