"""ExcelWriter — appends and updates rows in the burn table workbook."""

from __future__ import annotations

from pathlib import Path

from app.burn_table.models.burn_record import BurnRecord


class TableFullError(Exception):
    """Raised when all 34 data rows (A3:A36) are occupied."""


class ExcelWriter:
    """Writes BurnRecord data into the fixed-layout burn table workbook.

    Both .xls (xlrd + xlutils) and .xlsx (openpyxl) formats are supported.
    All writes are atomic: open → modify → save in a single call.
    """

    DATA_START_ROW = 3
    MAX_ROW = 36

    def append_record(self, path: Path, record: BurnRecord) -> int:
        """Append *record* to the next free row and save.

        Returns the 1-based Excel row number that was written.
        Raises TableFullError if no free row exists.
        """
        if path.suffix.lower() == ".xls":
            return self._append_xls(path, record)
        return self._append_xlsx(path, record)

    def update_record(self, path: Path, row_num: int, record: BurnRecord) -> None:
        """Overwrite an existing row with new data."""
        if not (self.DATA_START_ROW <= row_num <= self.MAX_ROW):
            raise ValueError(
                f"row_num {row_num} is outside data range "
                f"{self.DATA_START_ROW}–{self.MAX_ROW}."
            )
        if path.suffix.lower() == ".xls":
            self._update_xls(path, row_num, record)
        else:
            self._update_xlsx(path, row_num, record)

    # ── .xlsx ────────────────────────────────────────────────────────────────

    def _append_xlsx(self, path: Path, record: BurnRecord) -> int:
        import openpyxl

        try:
            wb = openpyxl.load_workbook(path)
        except Exception as exc:
            raise ValueError(f"Cannot open workbook '{path}': {exc}") from exc

        ws = wb.active
        next_row = self._find_next_free_xlsx(ws)
        if next_row is None:
            raise TableFullError(
                "The burn table is full (rows A3–A36 are all occupied)."
            )
        self._write_row_xlsx(ws, next_row, record)
        wb.save(path)
        return next_row

    def _update_xlsx(self, path: Path, row_num: int, record: BurnRecord) -> None:
        import openpyxl

        wb = openpyxl.load_workbook(path)
        ws = wb.active
        self._write_row_xlsx(ws, row_num, record)
        wb.save(path)

    def _find_next_free_xlsx(self, ws) -> int | None:
        for row_num in range(self.DATA_START_ROW, self.MAX_ROW + 1):
            if ws.cell(row=row_num, column=1).value is None:
                return row_num
        return None

    def _write_row_xlsx(self, ws, row_num: int, record: BurnRecord) -> None:
        for col_idx, value in enumerate(record.to_row(), start=1):
            ws.cell(row=row_num, column=col_idx, value=value or None)

    # ── .xls ─────────────────────────────────────────────────────────────────

    def _append_xls(self, path: Path, record: BurnRecord) -> int:
        try:
            import xlrd
            from xlutils.copy import copy as xl_copy
        except ImportError as exc:
            raise ImportError(
                "xlrd and xlutils are required: pip install xlrd==1.2.0 xlutils"
            ) from exc

        try:
            rb = xlrd.open_workbook(str(path), formatting_info=True)
        except Exception as exc:
            raise ValueError(f"Cannot open workbook '{path}': {exc}") from exc

        rs = rb.sheet_by_index(0)
        next_row_idx = self._find_next_free_xls(rs)
        if next_row_idx is None:
            raise TableFullError(
                "The burn table is full (rows A3–A36 are all occupied)."
            )

        wb = xl_copy(rb)
        ws = wb.get_sheet(0)
        self._write_row_xls(ws, next_row_idx, record)
        wb.save(str(path))
        return next_row_idx + 1  # convert 0-based → 1-based Excel row

    def _update_xls(self, path: Path, row_num: int, record: BurnRecord) -> None:
        try:
            import xlrd
            from xlutils.copy import copy as xl_copy
        except ImportError as exc:
            raise ImportError(
                "xlrd and xlutils are required: pip install xlrd==1.2.0 xlutils"
            ) from exc

        rb = xlrd.open_workbook(str(path), formatting_info=True)
        wb = xl_copy(rb)
        ws = wb.get_sheet(0)
        self._write_row_xls(ws, row_num - 1, record)  # 1-based → 0-based
        wb.save(str(path))

    def _find_next_free_xls(self, ws) -> int | None:
        # xlrd is 0-indexed; rows beyond ws.nrows are implicitly empty
        for row_idx in range(self.DATA_START_ROW - 1, self.MAX_ROW):
            if row_idx >= ws.nrows or not str(ws.cell_value(row_idx, 0)).strip():
                return row_idx
        return None

    def _write_row_xls(self, ws, row_idx: int, record: BurnRecord) -> None:
        for col_idx, value in enumerate(record.to_row()):
            if value is not None and value != "":
                ws.write(row_idx, col_idx, value)

    # ── clear all data rows ───────────────────────────────────────────────────

    def clear_all_records(self, path: Path) -> None:
        """Erase all data rows (rows 3–36) from *path*, preserving the header."""
        if path.suffix.lower() == ".xls":
            self._clear_xls(path)
        else:
            self._clear_xlsx(path)

    def _clear_xlsx(self, path: Path) -> None:
        import openpyxl

        wb = openpyxl.load_workbook(path)
        ws = wb.active
        for row_num in range(self.DATA_START_ROW, self.MAX_ROW + 1):
            for col in range(1, 11):
                ws.cell(row=row_num, column=col).value = None
        wb.save(path)

    def _clear_xls(self, path: Path) -> None:
        try:
            import xlrd
            from xlutils.copy import copy as xl_copy
        except ImportError as exc:
            raise ImportError(
                "xlrd and xlutils are required: pip install xlrd==1.2.0 xlutils"
            ) from exc

        rb = xlrd.open_workbook(str(path), formatting_info=True)
        rs = rb.sheet_by_index(0)
        wb = xl_copy(rb)
        ws = wb.get_sheet(0)
        limit = min(self.MAX_ROW, rs.nrows)
        for row_idx in range(self.DATA_START_ROW - 1, limit):
            for col_idx in range(10):
                ws.write(row_idx, col_idx, "")
        wb.save(str(path))
