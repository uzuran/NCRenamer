"""Shared openpyxl style and print-layout helpers for the burn table workbook.

All openpyxl imports are deferred so this module loads even when openpyxl
is not installed (e.g. when the .xls path is used exclusively).
"""

from __future__ import annotations


def make_border():
    from openpyxl.styles import Border, Side
    thin = Side(style="thin")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def make_center_alignment(wrap: bool = False):
    from openpyxl.styles import Alignment
    return Alignment(horizontal="center", vertical="center", wrap_text=wrap)


def apply_cell_style(cell, *, border, alignment) -> None:
    """Apply border and alignment to a single openpyxl cell."""
    cell.border = border
    cell.alignment = alignment


def apply_print_settings(ws) -> None:
    """Configure landscape A4 layout, fit to width, print area A1:I36."""
    ws.print_area = "A1:I36"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = 9          # 9 = A4 in openpyxl
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0        # 0 = unlimited pages tall (fit to width only)
    ws.sheet_properties.pageSetupPr.fitToPage = True
    # Narrow margins so the 10-column table fits on one A4 sheet in landscape
    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.6
    ws.page_margins.bottom = 0.6
    ws.page_margins.header = 0.2
    ws.page_margins.footer = 0.2
