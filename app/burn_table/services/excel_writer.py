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
            if ws.cell(row=row_num, column=2).value is None:  # column B = program_number
                return row_num
        return None

    def _write_row_xlsx(self, ws, row_num: int, record: BurnRecord) -> None:
        from app.burn_table.services._xlsx_format import make_border, make_center_alignment
        border = make_border()
        center = make_center_alignment()
        for col_idx, value in enumerate(record.to_row(), start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=value or None)
            cell.border = border
            cell.alignment = center

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
        # xlrd is 0-indexed; rows beyond ws.nrows are implicitly empty.
        # Use column B (program_number, index 1) as the occupied-row marker —
        # column A (date) can be empty for 2nd+ records by design.
        for row_idx in range(self.DATA_START_ROW - 1, self.MAX_ROW):
            if row_idx >= ws.nrows or not str(ws.cell_value(row_idx, 1)).strip():
                return row_idx
        return None

    def _write_row_xls(self, ws, row_idx: int, record: BurnRecord) -> None:
        import xlwt
        # Style must be passed explicitly — calling ws.write() without a style
        # resets the cell to xlwt defaults and destroys the existing borders.
        data_style = xlwt.easyxf(
            "alignment: horiz centre, vert centre;"
            "borders: left thin, right thin, top thin, bottom thin;"
        )
        for col_idx, value in enumerate(record.to_row()):
            ws.write(row_idx, col_idx, value if (value is not None and value != "") else "", data_style)

    # ── header migration ─────────────────────────────────────────────────────

    def update_header(self, path: Path) -> None:
        """Rewrite row 1 of an existing file with current headers and formatting.

        All data rows (3–36) are untouched.  Safe to call on old files.
        """
        if path.suffix.lower() == ".xls":
            self._update_header_xls(path)
        else:
            self._update_header_xlsx(path)

    def _update_header_xlsx(self, path: Path) -> None:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill

        from app.burn_table.services._xlsx_format import apply_print_settings, make_border
        from app.burn_table.services.table_factory import (
            _COL_WIDTHS, _HEADER_ROW_HEIGHT, _ROW1_HEADERS,
        )

        wb = openpyxl.load_workbook(path)
        ws = wb.active

        # Migrate old 10-column format: if F1 is "Čas progr. min", shift data
        # columns G-J left by one (G→F, H→G, I→H, J→I) for all data rows.
        f1 = str(ws.cell(row=1, column=6).value or "").strip().lower()
        if "čas" in f1 and "progr" in f1 and "celkov" not in f1:
            for row_num in range(3, 37):
                for src, dst in ((7, 6), (8, 7), (9, 8), (10, 9)):
                    ws.cell(row=row_num, column=dst).value = ws.cell(row=row_num, column=src).value

        # Strip column J completely — no value, no border, no fill (rows 1–36)
        no_border = Border()
        no_fill = PatternFill(fill_type=None)
        for row_num in range(1, 37):
            j = ws.cell(row=row_num, column=10)
            j.value = None
            j.border = no_border
            j.fill = no_fill

        header_font  = Font(bold=True, size=9, color="000000")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_fill  = PatternFill("solid", fgColor="FFFFFF")
        border       = make_border()

        for col_idx, (header, width) in enumerate(zip(_ROW1_HEADERS, _COL_WIDTHS), start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font      = header_font
            cell.fill      = header_fill
            cell.alignment = header_align
            cell.border    = border
            ws.column_dimensions[cell.column_letter].width = width

        ws.row_dimensions[1].height = _HEADER_ROW_HEIGHT
        apply_print_settings(ws)
        wb.save(path)

    def _update_header_xls(self, path: Path) -> None:
        try:
            import xlrd
            import xlwt
            from xlutils.copy import copy as xl_copy
        except ImportError as exc:
            raise ImportError(
                "xlrd and xlutils are required: pip install xlrd==1.2.0 xlutils"
            ) from exc

        from app.burn_table.services.table_factory import (
            _COL_WIDTHS, _HEADER_ROW_HEIGHT, _ROW1_HEADERS,
        )

        rb = xlrd.open_workbook(str(path), formatting_info=True)
        rs = rb.sheet_by_index(0)
        wb = xl_copy(rb)
        ws = wb.get_sheet(0)

        blank_style = xlwt.easyxf("")  # no borders, no fill — truly empty cell

        # Migrate old 10-column format: shift data columns G-J left by one
        f1_old = str(rs.cell_value(0, 5) if rs.nrows > 0 and rs.ncols > 5 else "").strip().lower()
        if "čas" in f1_old and "progr" in f1_old and "celkov" not in f1_old:
            data_style = xlwt.easyxf(
                "alignment: horiz centre, vert centre;"
                "borders: left thin, right thin, top thin, bottom thin;"
            )
            limit = min(self.MAX_ROW, rs.nrows)
            for row_idx in range(self.DATA_START_ROW - 1, limit):
                for src, dst in ((6, 5), (7, 6), (8, 7), (9, 8)):
                    val = rs.cell_value(row_idx, src) if rs.ncols > src else ""
                    ws.write(row_idx, dst, val, data_style)
                ws.write(row_idx, 9, "", blank_style)  # J — empty and unstyled

        header_style = xlwt.easyxf(
            "font: bold True, height 180, colour black;"
            "alignment: wrap True, horiz centre, vert centre;"
            "pattern: pattern solid, fore_colour white;"
            "borders: left thin, right thin, top thin, bottom thin;"
        )

        for col_idx, (header, width) in enumerate(zip(_ROW1_HEADERS, _COL_WIDTHS)):
            ws.write(0, col_idx, header, header_style)
            ws.col(col_idx).width = width * 256
        ws.write(0, 9, "", blank_style)  # J1 — empty and unstyled

        ws.row(0).height = _HEADER_ROW_HEIGHT * 20
        wb.save(str(path))

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
            for col in range(1, 10):
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
            for col_idx in range(9):
                ws.write(row_idx, col_idx, "")
        wb.save(str(path))
