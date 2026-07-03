"""FreeSlotDetector — counts used/free rows and produces a TableStatus."""

from __future__ import annotations

from pathlib import Path

from app.burn_table.models.table_status import TableStatus


class FreeSlotDetector:
    """Inspects the workbook and returns a TableStatus snapshot.

    Rules:
        - Data rows are A3–A36  (34 rows maximum).
        - A row is *used* when its column B (program_number) cell is non-empty.
          Column A (date) is intentionally empty for 2nd+ records by design.
        - free_rows  = 34 - used_rows
        - warning    = 'warning'  when free_rows ≤ 5
        - warning    = 'critical' when free_rows ≤ 2
        - is_full    = True       when free_rows == 0

    Both .xls (xlrd) and .xlsx (openpyxl) formats are supported.
    """

    DATA_START_ROW = 3
    MAX_ROW = 36
    MAX_DATA_ROWS = 34

    WARNING_THRESHOLD = 5
    CRITICAL_THRESHOLD = 2

    def __init__(self, sheet_index: int = 0) -> None:
        self._sheet_index = sheet_index

    def detect(self, path: Path) -> TableStatus:
        """Open *path* and return the current TableStatus."""
        if path.suffix.lower() == ".xls":
            return self._detect_xls(path)
        return self._detect_xlsx(path)

    def detect_from_records(self, record_count: int) -> TableStatus:
        """Build a TableStatus from a pre-counted record count (no file I/O)."""
        return self._build_status(record_count)

    # ── .xlsx ────────────────────────────────────────────────────────────────

    def _detect_xlsx(self, path: Path) -> TableStatus:
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError("openpyxl is required: pip install openpyxl") from exc

        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            raise ValueError(f"Cannot open workbook '{path}': {exc}") from exc

        ws = wb.worksheets[self._sheet_index]
        used_rows = sum(
            1
            for row_num in range(self.DATA_START_ROW, self.MAX_ROW + 1)
            if ws.cell(row=row_num, column=2).value is not None  # column B = program_number
        )
        wb.close()
        return self._build_status(used_rows)

    # ── .xls ─────────────────────────────────────────────────────────────────

    def _detect_xls(self, path: Path) -> TableStatus:
        try:
            import xlrd
        except ImportError as exc:
            raise ImportError("xlrd is required: pip install xlrd==1.2.0") from exc

        try:
            wb = xlrd.open_workbook(str(path))
        except Exception as exc:
            raise ValueError(f"Cannot open workbook '{path}': {exc}") from exc

        ws = wb.sheet_by_index(self._sheet_index)
        limit = min(self.MAX_ROW, ws.nrows)
        used_rows = sum(
            1
            for row_idx in range(self.DATA_START_ROW - 1, limit)
            if str(ws.cell_value(row_idx, 1)).strip()  # column B (index 1) = program_number
        )
        return self._build_status(used_rows)

    # ── shared ───────────────────────────────────────────────────────────────

    def _build_status(self, used_rows: int) -> TableStatus:
        free_rows = max(0, self.MAX_DATA_ROWS - used_rows)
        is_full = free_rows == 0

        if free_rows <= self.CRITICAL_THRESHOLD:
            warning = "critical"
        elif free_rows <= self.WARNING_THRESHOLD:
            warning = "warning"
        else:
            warning = ""

        return TableStatus(
            used_rows=used_rows,
            free_rows=free_rows,
            is_full=is_full,
            warning=warning,
        )
