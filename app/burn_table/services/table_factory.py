"""TableFactory — creates a new, correctly formatted burn table workbook."""

from __future__ import annotations

from pathlib import Path


# Column headers: row 1 main headers, row 2 sub-headers (detail labels)
_ROW1_HEADERS = [
    "datum\npálení",          # A
    "číslo\nprogr.",          # B
    "",                        # C (note / free)
    "formát tabule\ndélka x šířka",  # D
    "počet\ntabuli\nks",      # E
    "čas\nprogr.\nmin",       # F
    "celkový\nčas prog.",     # G
    "vypáleno",               # H
    "druh\nvýrobku\nskupina", # I
    "pálil",                  # J
]

_COL_WIDTHS = [14, 12, 10, 32, 8, 10, 14, 10, 18, 12]  # approximate char widths


class TableFactory:
    """Builds a blank burn table workbook with the correct header layout.

    The resulting file has:
        - Row 1  : main column headers (wrapped text)
        - Row 2  : empty (reserved for sub-headers added manually)
        - Rows 3–36: empty data area
        - Columns A–J fixed widths
    """

    def create(self, path: Path) -> None:
        """Write a new, empty burn table workbook to *path*.

        If a file already exists at *path* it is overwritten.
        Both .xls and .xlsx formats are supported — detected from *path* suffix.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".xls":
            self._create_xls(path)
        else:
            self._create_xlsx(path)

    # ── .xlsx ────────────────────────────────────────────────────────────────

    def _create_xlsx(self, path: Path) -> None:
        try:
            import openpyxl
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError as exc:
            raise ImportError("openpyxl is required: pip install openpyxl") from exc

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pálení"

        header_font = Font(bold=True, size=9)
        header_fill = PatternFill("solid", fgColor="D9E1F2")
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col_idx, (header, width) in enumerate(
            zip(_ROW1_HEADERS, _COL_WIDTHS), start=1
        ):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            ws.column_dimensions[cell.column_letter].width = width

        ws.row_dimensions[1].height = 42

        try:
            from openpyxl.styles.borders import Border, Side
            thin = Side(style="thin")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)
            for row_num in range(1, 37):
                for col_num in range(1, 11):
                    ws.cell(row=row_num, column=col_num).border = border
        except Exception:
            pass

        wb.save(path)

    # ── .xls ─────────────────────────────────────────────────────────────────

    def _create_xls(self, path: Path) -> None:
        try:
            import xlwt
        except ImportError as exc:
            raise ImportError("xlwt is required: pip install xlwt") from exc

        wb = xlwt.Workbook(encoding="utf-8")
        ws = wb.add_sheet("Pálení")

        header_style = xlwt.easyxf(
            "font: bold True, height 180;"
            "alignment: wrap True, horiz centre, vert centre;"
            "pattern: pattern solid, fore_colour light_blue;"
            "borders: left thin, right thin, top thin, bottom thin;"
        )
        data_style = xlwt.easyxf(
            "borders: left thin, right thin, top thin, bottom thin;"
        )

        for col_idx, (header, width) in enumerate(zip(_ROW1_HEADERS, _COL_WIDTHS)):
            ws.write(0, col_idx, header.replace("\n", " "), header_style)
            ws.col(col_idx).width = width * 256  # xlwt unit = 1/256 of char width

        ws.row(0).height = 42 * 20  # xlwt unit = 1/20 pt
        wb.save(str(path))
