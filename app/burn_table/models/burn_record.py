"""BurnRecord - one data row (columns A-I) in the burn table."""

from dataclasses import dataclass, field


@dataclass
class BurnRecord:
    """Represents a single entry in the burn-cutting production table.

    Columns match the fixed Excel layout A-I:
        A - date (Czech format  e.g. 'Y2026M 6D30')
        B - program_number      e.g. '6670-18'
        C - note                free-text comment
        D - sheet_format        e.g. '1.0037 5.00T 1700.00X 1500.00'
        E - sheet_count         number of sheets
        F - total_time          raw time code e.g. 'H21M51S'
        G - burned              completion / burned-off note
        H - product_group       product type and group
        I - operator            name of the operator who ran the job

    program_time is kept as an in-memory field (parsed from NC) but is no
    longer written to Excel.
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
        return not any(
            [
                self.date,
                self.program_number,
                self.sheet_format,
                self.total_time,
            ]
        )

    def to_row(self) -> list[str | int]:
        """Return a flat list suitable for writing to a single Excel row (9 columns A-I)."""
        return [
            self.date,
            self.program_number,
            self.note,
            self.sheet_format,
            self.sheet_count if self.sheet_count else "",
            self.total_time,
            self.burned,
            self.product_group,
            self.operator,
        ]

    @classmethod
    def from_row(cls, row: list) -> "BurnRecord":
        """Construct a BurnRecord from a flat list of cell values (A-I or legacy A-J)."""

        def _str(val: object) -> str:
            return str(val).strip() if val is not None else ""

        def _int(val: object) -> int:
            try:
                return int(val)  # type: ignore[call-overload, no-any-return]
            except (TypeError, ValueError):
                return 0

        # Old 10-column format had program_time at F (index 5) and operator at J (index 9).
        # Detect it by a non-empty J cell.
        if len(row) >= 10 and row[9] is not None and str(row[9]).strip():
            return cls(
                date=_str(row[0]),
                program_number=_str(row[1]),
                note=_str(row[2]),
                sheet_format=_str(row[3]),
                sheet_count=_int(row[4]),
                program_time=_str(row[5]),
                total_time=_str(row[6]),
                burned=_str(row[7]),
                product_group=_str(row[8]),
                operator=_str(row[9]),
            )

        # New 9-column format: A-I, no program_time column
        return cls(
            date=_str(row[0] if len(row) > 0 else None),
            program_number=_str(row[1] if len(row) > 1 else None),
            note=_str(row[2] if len(row) > 2 else None),
            sheet_format=_str(row[3] if len(row) > 3 else None),
            sheet_count=_int(row[4] if len(row) > 4 else None),
            total_time=_str(row[5] if len(row) > 5 else None),
            burned=_str(row[6] if len(row) > 6 else None),
            product_group=_str(row[7] if len(row) > 7 else None),
            operator=_str(row[8] if len(row) > 8 else None),
        )
